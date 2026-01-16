import { useState } from 'react';
import { WelcomePage } from './pages/WelcomePage';
import { ChatPage } from './pages/ChatPage';
import './assets/styles/anime-theme.css';

type Page = 'welcome' | 'chat';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('welcome');

  const handleStartChat = () => {
    setCurrentPage('chat');
  };

  const handleBackToWelcome = () => {
    setCurrentPage('welcome');
  };

  return (
    <>
      {currentPage === 'welcome' && (
        <WelcomePage onStartChat={handleStartChat} />
      )}
      {currentPage === 'chat' && (
        <ChatPage onBack={handleBackToWelcome} />
      )}
    </>
  );
}

export default App;
