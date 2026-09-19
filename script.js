let isChatOpen = false;
let isFirstOpen = true;

function toggleChat() {
    const chatbox = document.getElementById("chatbox");
    const chatIcon = document.getElementById("chat-icon");
    const notifDot = document.getElementById("notification-dot");
    const popupMsg = document.getElementById("chat-popup-msg");

    isChatOpen = !isChatOpen;

    if (isChatOpen) {
        chatbox.classList.remove("hidden");
        chatIcon.classList.remove("pulse");
        
        // Hide notifications when chat is opened
        if (notifDot) notifDot.classList.remove("show");
        if (popupMsg) popupMsg.classList.remove("show");

        if (isFirstOpen) {
            startChat();
            isFirstOpen = false;
        }
    } else {
        chatbox.classList.add("hidden");
    }
}

function scrollToBottom() {
    const messages = document.getElementById("messages");
    messages.scrollTo({
        top: messages.scrollHeight,
        behavior: 'smooth'
    });
}

function showTypingIndicator() {
    const msgDiv = document.getElementById("messages");

    const container = document.createElement("div");
    container.className = "msg-container bot-msg typing-container";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    container.appendChild(avatar);
    container.appendChild(indicator);
    msgDiv.appendChild(container);

    scrollToBottom();
    return container;
}

function addBotMessage(text) {
    const msgDiv = document.getElementById("messages");

    const container = document.createElement("div");
    container.className = "msg-container bot-msg";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const content = document.createElement("div");
    content.className = "msg-content";
    content.innerHTML = text;

    container.appendChild(avatar);
    container.appendChild(content);
    msgDiv.appendChild(container);

    scrollToBottom();
}

function addUserMessage(text) {
    const msgDiv = document.getElementById("messages");

    const container = document.createElement("div");
    container.className = "msg-container user-msg";

    const content = document.createElement("div");
    content.className = "msg-content";
    content.innerText = text;

    container.appendChild(content);
    msgDiv.appendChild(container);

    scrollToBottom();
}

async function startChat() {
    const typing = showTypingIndicator();

    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();

        setTimeout(() => {
            typing.remove();
            addBotMessage("👋 Welcome to the College Help Desk! Please select a category below:");
            showOptions(categories, (category) => fetchQuestions(category), false, true);
        }, 1000);

    } catch (error) {
        typing.remove();
        addBotMessage("Sorry, I'm having trouble connecting to the server.");
    }
}

function showOptions(options, onClickCallback, showBack = false, isGrid = false) {
    const msgDiv = document.getElementById("messages");

    const container = document.createElement("div");
    container.className = "options-container";
    if (isGrid) {
        container.classList.add("grid-options");
    }

    options.forEach((opt, index) => {
        const btn = document.createElement("button");
        btn.className = "chip-btn";
        btn.innerText = opt;
        btn.onclick = () => {
            // Remove options after selection to make chat cleaner
            container.remove();
            onClickCallback(opt, index);
        };
        container.appendChild(btn);
    });

    if (showBack) {
        const backBtn = document.createElement("button");
        backBtn.className = "chip-btn back-btn";
        backBtn.innerText = "⬅ Back to Categories";
        backBtn.onclick = () => {
            container.remove();
            startChat();
        };
        container.appendChild(backBtn);
    }

    msgDiv.appendChild(container);
    scrollToBottom();
}

async function fetchQuestions(category) {
    addUserMessage(category);
    const typing = showTypingIndicator();

    try {
        const response = await fetch(`/api/questions/${category}`);
        const questions = await response.json();

        setTimeout(() => {
            typing.remove();
            addBotMessage(`Here are the topics for ${category}:`);
            showOptions(questions, (question, index) => fetchAnswer(category, index, question), true);
        }, 800);

    } catch (error) {
        typing.remove();
        addBotMessage("Sorry, I couldn't fetch the questions.");
    }
}

async function fetchAnswer(category, index, questionText) {
    addUserMessage(questionText);
    const typing = showTypingIndicator();

    try {
        const response = await fetch(`/api/answer/${category}/${index}`);
        const data = await response.json();

        setTimeout(() => {
            typing.remove();
            addBotMessage(data.answer);

            // Show options to go back
            setTimeout(() => {
                showOptions(["More questions in " + category], () => fetchQuestions(category), true);
            }, 800);

        }, 1200);

    } catch (error) {
        typing.remove();
        addBotMessage("Sorry, I couldn't fetch the answer.");
    }
}

// Add pulse effect to chat icon initially
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("chat-icon").classList.add("pulse");
    
    // Show notification and popup after 3 seconds
    setTimeout(() => {
        if (!isChatOpen) {
            const notifDot = document.getElementById("notification-dot");
            const popupMsg = document.getElementById("chat-popup-msg");
            if (notifDot) notifDot.classList.add("show");
            if (popupMsg) popupMsg.classList.add("show");
        }
    }, 3000);
});

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        handleSearch();
    }
}

async function handleSearch() {
    const inputField = document.getElementById("chat-input");
    const query = inputField.value.trim();

    if (!query) return;

    addUserMessage(query);
    inputField.value = '';
    const typing = showTypingIndicator();

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const results = await response.json();

        setTimeout(() => {
            typing.remove();

            if (results.length === 0) {
                addBotMessage("Umm..I did not quite understand that");
                showOptions(["Back to Main Menu"], () => {
                    document.getElementById("messages").innerHTML = "";
                    startChat();
                });
            } else {
                addBotMessage(`Here are some related questions I found for "${query}":`);
                showSearchResults(results);
            }
        }, 800);

    } catch (error) {
        typing.remove();
        addBotMessage("Sorry, an error occurred while searching.");
    }
}

function showSearchResults(results) {
    const msgDiv = document.getElementById("messages");

    const container = document.createElement("div");
    container.className = "options-container";

    // Show all matching results as requested
    results.forEach((result) => {
        const btn = document.createElement("button");
        btn.className = "chip-btn";
        btn.innerText = result.question;
        btn.onclick = () => {
            container.remove();
            fetchAnswer(result.category, result.index, result.question);
        };
        container.appendChild(btn);
    });

    const backBtn = document.createElement("button");
    backBtn.className = "chip-btn back-btn";
    backBtn.innerText = "⬅ Back to Categories";
    backBtn.onclick = () => {
        container.remove();
        document.getElementById("messages").innerHTML = "";
        startChat();
    };
    container.appendChild(backBtn);

    msgDiv.appendChild(container);
    scrollToBottom();
}
