import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/TopBar";
import { ComicAssetsPage } from "./pages/ComicAssetsPage";
import { ComicDetailPage } from "./pages/ComicDetailPage";
import { ComicsPage } from "./pages/ComicsPage";
import { PageEditorPage } from "./pages/PageEditorPage";

export default function App() {
  return (
    <div className="app-shell">
      <TopBar />
      <main>
        <Routes>
          <Route path="/" element={<ComicsPage />} />
          <Route path="/comics/:comicId" element={<ComicDetailPage />} />
          <Route path="/comics/:comicId/assets" element={<ComicAssetsPage />} />
          <Route path="/pages/:pageId" element={<PageEditorPage />} />
        </Routes>
      </main>
    </div>
  );
}
