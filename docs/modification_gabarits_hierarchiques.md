# Modification — Gabarits hiérarchiques installables

## Objectif

Modifier l’état actuel de BD Creator pour remplacer la liste plate de gabarits par une hiérarchie en trois niveaux :

```txt
Groupe général
└── Sous-groupe
    └── Gabarit
```

Exemples :

```txt
Pleine page
└── Favoris
    └── Splash vertical
└── Building
    └── Grande case + bande inférieure

Classique
└── Favoris
    └── 4 cases équilibrées
└── Dialogue
    └── 6 cases régulières

Spéciaux
└── Favoris
└── Effets
    └── Page éclatée
```

Le but n’est pas de créer un éditeur de gabarits dans l’application.
Le but est de permettre d’installer des gabarits préparés en local, puis de les classer dans une hiérarchie éditable.

---

## État actuel à modifier

Actuellement, les gabarits sont plats.

Le modèle `Template` contient seulement :

```txt
id
name
columns
rows
```

Les cases sont définies par `Slot` via `template_id`.

L’API `/api/templates` renvoie une liste plate de gabarits.

La page de détail d’une BD utilise cette liste plate dans un simple `<select>` pour créer une planche.

Cette logique doit être modifiée, sans réécrire tout le projet.

---

## Nouveau principe produit

### 1. Les groupes sont éditables dans l’application

Tout utilisateur connecté peut :

- créer un groupe général ;
- renommer un groupe général ;
- supprimer un groupe général s’il est vide ;
- créer un sous-groupe dans un groupe général ;
- renommer un sous-groupe ;
- supprimer un sous-groupe s’il est vide.

Il n’y a pas encore de notion d’administrateur.

Tous les utilisateurs connectés manipulent donc le même référentiel global de groupes et de gabarits.

---

### 2. Les gabarits ne sont pas édités dans l’application

Un gabarit est développé en local, hors application.

Dans l’application, un utilisateur connecté peut seulement :

- uploader un gabarit ;
- l’installer dans un sous-groupe existant ;
- le supprimer s’il n’est utilisé par aucune planche.

Une fois installé, le gabarit est figé.

L’application ne doit pas permettre de modifier :

- `columns` ;
- `rows` ;
- les `slots` ;
- la géométrie ;
- la structure interne du gabarit.

Pour modifier un gabarit, il faut :

1. créer une nouvelle version en local ;
2. uploader cette nouvelle version ;
3. l’installer comme nouveau gabarit ;
4. utiliser ce nouveau gabarit pour les futures planches.

Aucune migration automatique des anciennes planches vers un nouveau gabarit.

---

## Modèle de données cible

### TemplateGroup

Ajouter une table :

```txt
TemplateGroup
- id
- parent_id nullable
- name
- sort_order
- created_at
```

Règles :

```txt
parent_id null       => groupe général, niveau 1
parent_id non null   => sous-groupe, niveau 2
```

La hiérarchie doit être limitée à deux niveaux de groupes.

Un sous-groupe ne peut pas contenir un autre sous-groupe.

---

### Template

Modifier la table existante :

```txt
Template
- id
- group_id
- name
- columns
- rows
- source_filename
- installed_at
- sort_order
```

Règles :

- `group_id` est obligatoire ;
- `group_id` doit pointer vers un sous-groupe, pas vers un groupe général ;
- un gabarit installé est non modifiable structurellement ;
- `name` peut éventuellement rester modifiable, mais il est préférable de le considérer figé aussi en V1 de cette modification.

---

### Slot

La table `Slot` reste liée à `Template`.

Aucun changement fonctionnel majeur n’est attendu sur les cases.

Les slots sont créés au moment de l’installation du gabarit.

---

## Suppression et protections

### Suppression d’un gabarit

Un gabarit peut être supprimé uniquement s’il n’est utilisé par aucune planche.

Condition :

```txt
Aucune Page ne référence Template.id via Page.template_id
```

Si le gabarit est utilisé, l’API doit refuser avec une erreur claire.

Exemple :

```txt
Impossible de supprimer ce gabarit : il est utilisé par une ou plusieurs planches.
```

---

### Suppression d’un sous-groupe

Un sous-groupe peut être supprimé uniquement s’il ne contient aucun gabarit.

Si le sous-groupe contient au moins un gabarit, l’API doit refuser.

---

### Suppression d’un groupe général

Un groupe général peut être supprimé uniquement s’il ne contient aucun sous-groupe.

Si le groupe contient au moins un sous-groupe, l’API doit refuser.

---

## Installation d’un gabarit

### Format d’upload attendu

Prévoir un format simple pour importer un gabarit.

Recommandation : fichier JSON.

Exemple :

```json
{
  "name": "4 cases équilibrées",
  "columns": 2,
  "rows": 2,
  "slots": [
    { "col_start": 1, "row_start": 1, "col_span": 1, "row_span": 1, "geometry_type": "rectangle" },
    { "col_start": 2, "row_start": 1, "col_span": 1, "row_span": 1, "geometry_type": "rectangle" },
    { "col_start": 1, "row_start": 2, "col_span": 1, "row_span": 1, "geometry_type": "rectangle" },
    { "col_start": 2, "row_start": 2, "col_span": 1, "row_span": 1, "geometry_type": "rectangle" }
  ]
}
```

Le fichier uploadé doit être validé côté backend avant insertion.

---

### Validation minimale

Le backend doit vérifier :

- `name` non vide ;
- `columns >= 1` ;
- `rows >= 1` ;
- au moins un slot ;
- chaque slot reste dans la grille ;
- `geometry_type = rectangle` pour l’instant ;
- `group_id` existe ;
- `group_id` pointe vers un sous-groupe.

---

## API à ajouter ou modifier

### Groupes

Ajouter :

```txt
GET    /api/template-groups
POST   /api/template-groups
PATCH  /api/template-groups/{group_id}
DELETE /api/template-groups/{group_id}
```

`GET /api/template-groups` doit permettre au front de reconstruire l’arborescence complète.

---

### Gabarits

Modifier ou compléter :

```txt
GET    /api/templates
POST   /api/templates/install
DELETE /api/templates/{template_id}
```

`GET /api/templates` ne doit plus forcément être pensé comme une simple liste plate.
Deux options acceptables :

#### Option A — garder une liste plate enrichie

Chaque gabarit contient :

```txt
id
name
columns
rows
group_id
group_name
parent_group_id
parent_group_name
slots
```

Le front regroupe ensuite les données.

#### Option B — renvoyer directement un arbre

```txt
Groupe général
- sous-groupes
  - templates
```

Pour cette modification, l’option A est plus simple et limite les changements.

---

## Frontend attendu

### Création d’une planche

Remplacer le select plat actuel par une sélection hiérarchique.

Comportement minimal acceptable :

```txt
1. choisir un groupe général
2. choisir un sous-groupe
3. choisir un gabarit
4. créer la planche
```

Ne pas chercher à faire une interface avancée.

Objectif : clarté et robustesse.

---

### Gestion des groupes

Ajouter une interface simple permettant de :

- lister les groupes généraux ;
- lister les sous-groupes ;
- créer / renommer / supprimer si autorisé.

Pas de drag & drop nécessaire.

`sort_order` peut être géré avec des boutons simples :

```txt
Monter
Descendre
```

ou laissé non exposé en première étape.

---

### Installation d’un gabarit

Ajouter une interface simple :

```txt
1. choisir un fichier JSON
2. choisir le sous-groupe d’installation
3. cliquer sur Installer
```

Après installation, le gabarit apparaît dans la hiérarchie.

---

## Migration de l’existant

Les gabarits actuels doivent être conservés.

Créer par défaut :

```txt
Classique
└── Base
```

Tous les gabarits existants doivent être rattachés à :

```txt
Classique / Base
```

Cela permet de ne pas casser les planches existantes.

---

## Règles de compatibilité

Les planches existantes doivent continuer à fonctionner.

`Page.template_id` reste la référence principale.

Ne pas casser :

- l’édition de planche ;
- l’affichage des cases ;
- la génération des artefacts ;
- l’invalidation des artefacts ;
- les BD déjà créées.

---

## Ce qu’il ne faut pas faire

Ne pas créer un éditeur graphique de gabarits.

Ne pas autoriser la modification des slots d’un gabarit installé.

Ne pas supprimer en cascade les planches utilisant un gabarit.

Ne pas supprimer en cascade les gabarits d’un sous-groupe.

Ne pas créer une hiérarchie infinie.

Ne pas ajouter de notion d’admin pour l’instant.

---

## Résultat attendu

À la fin de cette modification :

- les gabarits sont organisés en trois niveaux ;
- les groupes et sous-groupes sont éditables ;
- les gabarits sont installables par upload ;
- les gabarits installés sont figés ;
- les suppressions dangereuses sont interdites ;
- les planches existantes restent compatibles ;
- la création de planche utilise la nouvelle hiérarchie.

---

## Prompt court pour Codex

Implémente la modification décrite dans ce document sur l’état actuel du projet BD Creator.

Important : il ne s’agit pas de repartir de zéro. Il faut modifier le modèle existant `Template` / `Slot` / `Page.template_id`, ajouter une hiérarchie `TemplateGroup`, permettre l’installation de gabarits JSON dans un sous-groupe, et protéger les suppressions si des données dépendent encore du groupe ou du gabarit.

Garde l’application simple. Ne crée pas d’éditeur graphique de gabarits. Un gabarit installé est figé.
