import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api, postForm } from "../services/api";
import { Template, TemplateGroup } from "../types";

type GroupMap = Record<number, TemplateGroup[]>;

export function TemplateManagementPage() {
  const { t } = useI18n();
  const [groups, setGroups] = useState<TemplateGroup[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [topLevelName, setTopLevelName] = useState("");
  const [subgroupName, setSubgroupName] = useState("");
  const [subgroupParentId, setSubgroupParentId] = useState<number | null>(null);
  const [uploadGroupId, setUploadGroupId] = useState<number | null>(null);

  const topGroups = useMemo(() => groups.filter((g) => g.parent_id === null), [groups]);
  const subgroupsByParent = useMemo<GroupMap>(() => {
    const out: GroupMap = {};
    for (const group of groups) {
      if (group.parent_id === null) continue;
      out[group.parent_id] = out[group.parent_id] || [];
      out[group.parent_id].push(group);
    }
    return out;
  }, [groups]);

  async function load() {
    const [groupData, templateData] = await Promise.all([
      api.get<TemplateGroup[]>("/api/template-groups"),
      api.get<Template[]>("/api/templates"),
    ]);
    setGroups(groupData);
    setTemplates(templateData);
    const firstTop = groupData.find((g) => g.parent_id === null);
    const firstSub = groupData.find((g) => g.parent_id !== null);
    if (firstTop && subgroupParentId === null) setSubgroupParentId(firstTop.id);
    if (firstSub && uploadGroupId === null) setUploadGroupId(firstSub.id);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  async function onCreateTopGroup(e: FormEvent) {
    e.preventDefault();
    if (!topLevelName.trim()) return;
    try {
      await api.post("/api/template-groups", { name: topLevelName.trim() });
      setTopLevelName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onCreateSubgroup(e: FormEvent) {
    e.preventDefault();
    if (!subgroupName.trim() || subgroupParentId === null) return;
    try {
      await api.post("/api/template-groups", { name: subgroupName.trim(), parent_id: subgroupParentId });
      setSubgroupName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onRenameGroup(group: TemplateGroup) {
    const nextName = window.prompt("Nouveau nom", group.name);
    if (!nextName || !nextName.trim() || nextName.trim() === group.name) return;
    try {
      await api.patch(`/api/template-groups/${group.id}`, { name: nextName.trim() });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onDeleteGroup(groupId: number) {
    try {
      await api.del(`/api/template-groups/${groupId}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onInstallTemplate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (uploadGroupId === null) return;
    const form = new FormData(e.currentTarget);
    const file = form.get("template_file");
    if (!(file instanceof File)) {
      setError("Template file is required");
      return;
    }
    const payload = new FormData();
    payload.append("group_id", String(uploadGroupId));
    payload.append("file", file);
    try {
      await postForm("/api/templates/install", payload);
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onDeleteTemplate(templateId: number) {
    try {
      await api.del(`/api/templates/${templateId}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section className="card">
      <h2>{t("template_management")}</h2>
      <p><Link to="/">{t("back_home")}</Link></p>

      <h3>{t("template_groups")}</h3>
      <form className="row wrap" onSubmit={onCreateTopGroup}>
        <input value={topLevelName} onChange={(e) => setTopLevelName(e.target.value)} placeholder={t("new_top_group")} />
        <button>{t("create")}</button>
      </form>

      <form className="row wrap" onSubmit={onCreateSubgroup}>
        <select value={subgroupParentId ?? ""} onChange={(e) => setSubgroupParentId(Number(e.target.value))}>
          {topGroups.map((group) => (
            <option key={group.id} value={group.id}>{group.name}</option>
          ))}
        </select>
        <input value={subgroupName} onChange={(e) => setSubgroupName(e.target.value)} placeholder={t("new_subgroup")} />
        <button>{t("create")}</button>
      </form>

      <div className="list">
        {topGroups.map((group) => (
          <div key={group.id} className="card" style={{ padding: "10px" }}>
            <div className="row wrap">
              <strong>{group.name}</strong>
              <button type="button" onClick={() => onRenameGroup(group)}>{t("rename")}</button>
              <button type="button" onClick={() => onDeleteGroup(group.id)}>{t("delete")}</button>
            </div>
            <ul>
              {(subgroupsByParent[group.id] || []).map((subgroup) => (
                <li key={subgroup.id} className="row wrap">
                  <span>{subgroup.name}</span>
                  <button type="button" onClick={() => onRenameGroup(subgroup)}>{t("rename")}</button>
                  <button type="button" onClick={() => onDeleteGroup(subgroup.id)}>{t("delete")}</button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <h3>{t("install_template")}</h3>
      <form className="row wrap" onSubmit={onInstallTemplate}>
        <select value={uploadGroupId ?? ""} onChange={(e) => setUploadGroupId(Number(e.target.value))}>
          {groups.filter((g) => g.parent_id !== null).map((group) => (
            <option key={group.id} value={group.id}>{group.name}</option>
          ))}
        </select>
        <input type="file" name="template_file" accept="application/json" />
        <button>{t("install")}</button>
      </form>

      <h3>{t("templates")}</h3>
      <ul className="list">
        {templates.map((template) => (
          <li key={template.id} className="row wrap">
            <span>{template.parent_group_name} / {template.group_name} / {template.name}</span>
            <button type="button" onClick={() => onDeleteTemplate(template.id)}>{t("delete")}</button>
          </li>
        ))}
      </ul>

      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
