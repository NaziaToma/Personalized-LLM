import { useEffect, useState } from "react";
import Button from "react-bootstrap/Button";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    if (!sessionId) return;

    const intervalId = setInterval(async () => {
      const response = await fetch(
        `http://localhost:8000/api/chat/sessions/${sessionId}/`,
        {
          method: "GET",
        }
      );
      const data = await response.json();
      setMessages(data.messages);
    }, 1000);

    return () => clearInterval(intervalId);
  }, [sessionId]);

  const postMessage = async (sessionId, message) => {
    await fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: message }),
    });
  };

  const sendMessage = async (e) => {
    if (e.key === "Enter") {
      if (!sessionId) {
        const response = await fetch(
          "http://localhost:8000/api/chat/sessions/",
          {
            method: "POST",
          }
        );
        const data = await response.json();
        setSessionId(data.id);
        postMessage(data.id, message);
      } else {
        postMessage(sessionId, message);
      }

      setMessage("");
    }
  };

  return (
    <>
      <Button variant="primary">Primary</Button>
      <div className="wrapper">
        <div className="chat-wrapper">
          <div className="chat-history">
            <div>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message${message.role === "user" ? " user" : ""}`}
                >
                  {message.role === "user" ? "Me: " : "AI: "}
                  {message.content}
                </div>
              ))}
            </div>
          </div>
          <input
            type="text"
            placeholder="Type a message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyUp={sendMessage}
          />
        </div>
      </div>
    </>
  );
}

export default App;
