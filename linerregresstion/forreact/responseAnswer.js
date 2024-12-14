import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios, { AxiosError } from 'axios';
import './css/chatbot.css';

// Define types for improved type safety
interface Message {
  text: string;
  sender: 'bot' | 'user';
}

interface LanguageDetectionResponse {
  data: {
    detections: Array<{ language: string }>
  }
}

const DETECTION_API_KEY = process.env.REACT_APP_LANGUAGE_DETECTION_KEY || '';
const CHATBOT_API_ENDPOINT = process.env.REACT_APP_CHATBOT_API_ENDPOINT || '';

const ChatBot: React.FC = () => {
  // State management with more explicit types
  const [messages, setMessages] = useState<Message[]>([
    { text: 'こんばんは！！ご用件は何でしょうか？', sender: 'bot' },
  ]);
  const [question, setQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const [language, setLanguage] = useState<string>('ja-JP');
  const [isBotAnswerReady, setIsBotAnswerReady] = useState<boolean>(false);
  const [isVoiceInput, setIsVoiceInput] = useState<boolean>(false);

  // Memoized recognition to prevent unnecessary re-creations
  const recognition = useMemo(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = false;
    recognitionInstance.interimResults = false;
    recognitionInstance.lang = language;

    return recognitionInstance;
  }, [language]);

  // Improved language detection with error handling
  const detectLanguage = useCallback(async (text: string): Promise<string> => {
    try {
      const response = await axios.post<LanguageDetectionResponse>(
        'https://ws.detectlanguage.com/0.2/detect',
        {
          q: text,
          key: DETECTION_API_KEY
        }
      );
      return response.data.data.detections[0]?.language || 'en';
    } catch (error) {
      console.error("Language detection error:", error);
      return 'en';
    }
  }, []);

  // Speech recognition effect with better error handling
  useEffect(() => {
    if (!recognition) return;

    const handleResult = async (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;

      try {
        const detectedLanguage = await detectLanguage(transcript);
        setLanguage(detectedLanguage);
        recognition.lang = detectedLanguage;

        setQuestion(transcript);
        setIsListening(false);
        setIsVoiceInput(true);
      } catch (error) {
        console.error("Speech recognition processing error:", error);
        setIsListening(false);
      }
    };

    const handleError = (event: Event) => {
      console.error("Speech recognition error:", event);
      setIsListening(false);
    };

    recognition.addEventListener('result', handleResult as EventListener);
    recognition.addEventListener('error', handleError);

    return () => {
      recognition.removeEventListener('result', handleResult as EventListener);
      recognition.removeEventListener('error', handleError);
    };
  }, [recognition, detectLanguage]);

  // Centralized error handling for API requests
  const handleApiError = (error: AxiosError) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      setError(`Request failed: ${error.response.status} - ${error.response.data}`);
    } else if (error.request) {
      // The request was made but no response was received
      setError('No response from server. Check your network connection.');
    } else {
      // Something happened in setting up the request
      setError(`Error: ${error.message}`);
    }
  };

  // Retry logic with exponential backoff
  const makeRequestWithRetry = useCallback(async (retries = 3) => {
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        return await axios.post(CHATBOT_API_ENDPOINT, 
          { question }, 
          { 
            headers: { 'Content-Type': 'application/json' },
            timeout: 100000 
          }
        );
      } catch (error) {
        if (attempt === retries - 1) throw error;
        
        // Exponential backoff
        await delay(Math.pow(2, attempt) * 1000);
      }
    }
  }, [question]);

  // Text-to-Speech function with more robust checking
  const speak = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) {
      console.warn('Text-to-speech not supported');
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    window.speechSynthesis.speak(utterance);
  }, []);

  // Form submission handler
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) {
      setError('質問を入力してください。');
      return;
    }

    const userMessage: Message = { text: question, sender: 'user' };
    
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setError('');
    setQuestion('');
    setIsVoiceInput(false);

    try {
      const response = await makeRequestWithRetry();

      const botResponse = response.data.response?.map((item: any) => item.text).join(' ') || 'No answer found.';
      
      setMessages(prev => [
        ...prev,
        { text: botResponse, sender: 'bot' }
      ]);

      if (isVoiceInput) {
        speak(botResponse);
      } else {
        setIsBotAnswerReady(true);
      }
    } catch (error) {
      handleApiError(error as AxiosError);
    } finally {
      setLoading(false);
    }
  }, [question, isVoiceInput, makeRequestWithRetry, speak]);

  // Start speech recognition
  const startListening = useCallback(() => {
    if (recognition) {
      setIsListening(true);
      recognition.start();
    }
  }, [recognition]);

  return (
    <div className="chat-container">
      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={`chat-message ${msg.sender}`}>
            <div className="avatar">
              {msg.sender === 'bot' ? '🤖' : '👤'}
            </div>
            <span>{msg.text}</span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="chat-input-container">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question..."
          className="chat-input"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading} 
          className="chat-submit-button"
        >
          {loading ? '...' : '📩'}
        </button>

        <button
          type="button"
          onClick={startListening}
          disabled={loading || isListening}
          className="chat-mic-button"
        >
          <img src="/img/microphone.png" alt="microphone" />
        </button>
      </form>

      {isBotAnswerReady && !isVoiceInput && (
        <button
          type="button"
          onClick={() => speak(messages[messages.length - 1].text)}
          className="chat-sound-button"
        >
          🔊 Read Answer
        </button>
      )}

      {error && <p className="chat-error">{error}</p>}
    </div>
  );
};

export default ChatBot;