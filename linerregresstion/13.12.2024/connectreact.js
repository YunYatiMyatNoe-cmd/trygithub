import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './css/chatbot.css';

// Web Speech API (SpeechRecognition) Setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const ChatBot = () => {
    const [messages, setMessages] = useState([
        { text: 'こんばんは！！ご用件は何でしょうか？', sender: 'bot' },
    ]);
    const [question, setQuestion] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isListening, setIsListening] = useState(false);
    const [language, setLanguage] = useState('ja-JP');
    const [isVoiceInput, setIsVoiceInput] = useState(false);
    const [connected, setConnected] = useState(false); // WebSocket connection status
    const [webSocketError, setWebSocketError] = useState(null); // Store WebSocket errors
    const [retryCount, setRetryCount] = useState(0); // Track retry attempts for WebSocket

    const recognition = SpeechRecognition ? new SpeechRecognition() : null;
    const ws = useRef(null); // Ref for WebSocket instance

    // Setup SpeechRecognition if available
    if (recognition) {
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = language;
    }

    // Cleanup WebSocket connection if the component unmounts
    useEffect(() => {
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    // Start listening for speech input
    const startListening = () => {
        if (recognition) {
            setIsListening(true);
            recognition.start();
        }
    };

    // Detect language using external API
    const detectLanguage = async (text) => {
        try {
            const response = await axios.post(
                'https://ws.detectlanguage.com/0.2/detect',
                {
                    q: text,
                    key: 'YOUR_DETECTLANGUAGE_API_KEY' // Replace with your Detect Language API Key
                }
            );
            return response.data.data.detections[0].language;
        } catch (error) {
            console.error("Language detection error:", error);
            return 'ja'; // Default to Japanese
        }
    };

    // WebSocket connection handler
    const startWebSocket = (question) => {
        if (ws.current) {
            ws.current.close(); // Close any existing WebSocket connections
        }

        ws.current = new WebSocket('wss://dpyttqqe2e.execute-api.ap-northeast-1.amazonaws.com/production');  // Your API Gateway URL

        ws.current.onopen = () => {
            console.log('WebSocket connected');
            console.log("Connected with connectionId:", ws.protocol); 
            setConnected(true); // Set connection to true
            setWebSocketError(null); // Clear errors
            ws.current.send(JSON.stringify({ question })); // Send the question over WebSocket
            setRetryCount(0); // Reset retry count
        };

        ws.current.onclose = (event) => {
            console.log('WebSocket disconnected', event);
            setConnected(false);
            setWebSocketError(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);

            if (event.code === 1006 && retryCount < 5) {
                setRetryCount(retryCount + 1);
                const retryTimeout = Math.pow(2, retryCount) * 1000; // Exponential backoff
                console.log(`Retrying in ${retryTimeout / 1000} seconds...`);
                setTimeout(() => startWebSocket(question), retryTimeout);
            }
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
            setWebSocketError(`WebSocket error: ${error.message}`);
        };

        ws.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const botResponse = data.text;
            console.log(botResponse)
            setMessages((prevMessages) => [
                ...prevMessages,
                { text: botResponse, sender: 'bot' },
            ]);
            if (isVoiceInput) {
                speak(botResponse);
            }
        };
    };

    // Handle form submission
    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!question.trim()) {
            setError('質問を書いてください!');
            return;
        }

        const userMessage = { text: question, sender: 'user' };
        setMessages((prevMessages) => [...prevMessages, userMessage]);
        setLoading(true);
        setError('');
        setQuestion('');
        setIsVoiceInput(false);

        try {
            startWebSocket(question); // Start WebSocket connection to stream bot responses
        } catch (err) {
            console.error('Error:', err);
            setError('An error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Speak the text (using SpeechSynthesis API)
    const speak = (text) => {
        if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ja-JP'; // Force Japanese language to be used
            window.speechSynthesis.speak(utterance); // Speak the text
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-box">
                {messages.map((msg, index) => (
                    <div key={index} className={`chat-message ${msg.sender}`}>
                        {msg.sender === 'bot' ? (
                            <div className="avatar">🤖</div>
                        ) : (
                            <div className="avatar">👤</div>
                        )}
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
                />
                <button type="submit" disabled={loading} className="chat-submit-button">
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

            {error && <p className="chat-error">{error}</p>}

            {/* Display WebSocket connection status */}
            <div className="connection-status">
                {connected ? (
                    <span style={{ color: 'green' }}>✅ WebSocket Connected</span>
                ) : (
                    <span style={{ color: 'red' }}>❌ WebSocket Disconnected</span>
                )}
            </div>

            {/* Display WebSocket error message */}
            {webSocketError && (
                <div className="websocket-error">
                    <span style={{ color: 'red' }}>{`Error: ${webSocketError}`}</span>
                </div>
            )}
        </div>
    );
};

export default ChatBot;
