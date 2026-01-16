/** Main chat page component */

import React, { useState, useEffect } from 'react';
import { MessageList, ChatInput } from '../components/chat';
import { CharacterAvatar, CharacterInfoModal } from '../components/character';
import { ChatHistory } from '../components/history';
import { FloatingActionButton } from '../components/ui';
import { useChat } from '../hooks/useChat';
import { useCharacter } from '../hooks/useCharacter';

interface ChatPageProps {
  onBack: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({ onBack }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const { messages, loading, send, clearHistory } = useChat('sister_001');
  const { character } = useCharacter('sister_001');

  // Send greeting on first load
  useEffect(() => {
    if (messages.length === 0) {
      setTimeout(() => {
        send('你好');
      }, 500);
    }
  }, []);

  const handleSend = (message: string) => {
    send(message);
  };

  const handleClearHistory = () => {
    clearHistory();
    setShowHistory(false);
  };

  return (
    <div className="h-screen flex flex-col bg-gradient-to-b from-pink-50 to-white">
      {/* Header */}
      <div className="bg-white border-b-2 border-pink-100 px-4 py-3 flex items-center gap-3 shadow-sm">
        <button
          onClick={onBack}
          className="text-pink-500 hover:text-pink-600 transition-colors p-1"
        >
          ← 返回
        </button>
        <CharacterAvatar size="small" />
        <div className="flex-1">
          <h2 className="font-semibold text-gray-800">{character?.name || '妹妹'}</h2>
          <p className="text-xs text-green-500">在线</p>
        </div>
      </div>

      {/* Messages */}
      <MessageList messages={messages} isLoading={loading} />

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={loading}
        placeholder="和妹妹聊聊天吧～"
      />

      {/* Floating Buttons */}
      <FloatingActionButton
        onClick={() => setShowInfo(true)}
        icon="ℹ️"
        ariaLabel="角色信息"
        position="top-right"
      />
      <FloatingActionButton
        onClick={() => setShowHistory(true)}
        icon="📋"
        ariaLabel="对话历史"
        position="top-left"
      />

      {/* Modals */}
      <CharacterInfoModal
        isOpen={showInfo}
        onClose={() => setShowInfo(false)}
        character={character}
      />
      <ChatHistory
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        messages={messages}
        onClear={handleClearHistory}
      />
    </div>
  );
};
