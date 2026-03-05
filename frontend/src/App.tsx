import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { CharacterManagementPage } from './pages/CharacterManagementPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/characters" element={<CharacterManagementPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
