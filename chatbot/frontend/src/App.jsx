import { useEffect, useState } from "react";
import Button from "react-bootstrap/Button";
import Modal from "react-bootstrap/Modal";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

const personalizedQuestions = [
  {
    title: "Personalized Question 1",
    text: "Do you prefer direct next steps or detailed discussion first?",
    options: ["Direct steps", "Detailed discussion"],
  },
  {
    title: "Personalized Question 2",
    text: "Would you prefer a checklist or conversation?",
    options: ["Checklist", "Conversation"],
  },
];

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const [showModal, setShowModal] = useState(true);

  // --- State for managing the multi-question flow ---
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userChoices, setUserChoices] = useState([]);

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

  // 2. This function now handles an answer and decides whether to ask the next question or start the chat.
  const handleAnswer = (choice) => {
    const newChoices = [...userChoices, choice];
    setUserChoices(newChoices);

    // Check if there are more questions to ask
    if (currentQuestionIndex < personalizedQuestions.length - 1) {
      // Move to the next question
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // This was the last question, now start the chat with all collected choices
      startChat(newChoices);
    }
  };

  // 3. The startChat function now sends an array of choices.
  const startChat = async (finalChoices) => {
    try {
      const response = await fetch("http://localhost:8000/api/chat/sessions/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Send all collected choices in an array.
        // Note: The key is now "choices" (plural).
        body: JSON.stringify({ choices: finalChoices }),
      });
      const data = await response.json();
      setSessionId(data.id);
      setShowModal(false); // Close the modal
    } catch (error) {
      console.error("Error starting chat session:", error);
    }
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

  // Get the current question object to display in the modal
  const currentQuestion = personalizedQuestions[currentQuestionIndex];

  return (
    <>
      {/* --- This is the new, dynamic modal --- */}
      <Modal show={showModal} backdrop="static" keyboard={false} centered>
        <Modal.Header>
          {/* Display the title of the current question */}
          <Modal.Title>{currentQuestion.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* Display the text of the current question */}
          <p>{currentQuestion.text}</p>
        </Modal.Body>
        <Modal.Footer>
          {/* Dynamically create a button for each option of the current question */}
          {currentQuestion.options.map((option, index) => (
            <Button
              key={index}
              variant="primary"
              onClick={() => handleAnswer(option)}
            >
              {option}
            </Button>
          ))}
        </Modal.Footer>
      </Modal>

      <div className="wrapper">
        <div className="chat-wrapper">
          <div className="chat-history">
            <div>
              {/* --- THIS IS THE SECTION TO FIX --- */}
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message${message.role === "user" ? " user" : ""}`}
                >
                  <strong>{message.role === "user" ? "You" : "AI"}: </strong>
                  {/* Check the role: if it's not the user, render with Markdown */}
                  {message.role !== "user" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    // Otherwise, just display the user's text as is
                    <span>{message.content}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
          <input
            type="text"
            className="chat-input"
            placeholder={
              sessionId
                ? "Type a message..."
                : "Please answer the questions to begin."
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyUp={sendMessage}
            disabled={!sessionId}
          />
        </div>
      </div>
    </>
  );
}

export default App;
