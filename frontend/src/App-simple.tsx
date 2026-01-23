import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="*" element={<div className="p-8 text-center"><h1>페이지를 찾을 수 없습니다</h1></div>} />
      </Routes>
    </Router>
  );
}

export default App;
