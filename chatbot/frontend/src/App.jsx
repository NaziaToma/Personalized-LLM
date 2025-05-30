import { useState } from "react";

import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);

  const sendMessage = (e) => {
    if (e.key === "Enter") {
      setMessage("");
      setMessages([...messages, { content: message, role: "user" }]);
    }
  };

  return (
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
  );
}

export default App;
