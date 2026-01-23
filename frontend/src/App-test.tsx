import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={
          <div className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                Defense Intelligent Agent Platform
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                React 앱이 정상적으로 로드되었습니다.
              </p>
            </div>
          </div>
        } />
      </Routes>
    </Router>
  );
}

export default App;
