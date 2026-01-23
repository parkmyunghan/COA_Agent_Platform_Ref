import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';
import { ExecutionProvider } from './contexts/ExecutionContext';
import { SystemDataProvider } from './contexts/SystemDataContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import LandingPage from './pages/LandingPage';
import CommandControlPage from './pages/CommandControlPage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import DataManagementPage from './pages/DataManagementPage';
import OntologyStudioPage from './pages/OntologyStudioPage';
import RAGManagementPage from './pages/RAGManagementPage';
import LearningGuidePage from './pages/LearningGuidePage';

ModuleRegistry.registerModules([AllCommunityModule]);

function App() {
  return (
    <ErrorBoundary>
      <SystemDataProvider>
        <ExecutionProvider>
          <Router>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/dashboard" element={<CommandControlPage />} />
              <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
              <Route path="/data-management" element={<DataManagementPage />} />
              <Route path="/ontology-studio" element={<OntologyStudioPage />} />
              <Route path="/rag-management" element={<RAGManagementPage />} />
              <Route path="/learning-guide" element={<LearningGuidePage />} />
            </Routes>
          </Router>
        </ExecutionProvider>
      </SystemDataProvider>
    </ErrorBoundary>
  );
}

export default App;
