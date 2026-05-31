# UI chatbot
Web application UI for the AltGAN rag chatbot
<h1 id="ui_chatbot">UI Chatbot</h1>
<p>UI_Chatbot is a React-based chat interface that allows users to interact with an AI model, specifically tailored for queries related to Finance and Oil &amp; Gas industries.</p>
<h2 id="features">Features</h2>
<ul>
<li>Interactive chat interface</li>
<li>Category-based responses (Finance and Oil &amp; Gas)</li>
<li>Markdown rendering for bot responses</li>
<li>Citation support with clickable sources</li>
<li>Related questions suggestions</li>
<li>Chat history management (new chat, rename, delete)</li>
<li>Copy to clipboard functionality</li>
<li>Responsive design</li>
</ul>
<h2 id="technologies-used">Technologies Used</h2>
<ul>
<li>React</li>
<li>TypeScript</li>
<li>react-markdown for rendering markdown</li>
<li>react-helmet for managing document head</li>
<li>styled-components for styling</li>
</ul>
<h2 id="components">Components</h2>
<h3 id="main-components">Main Components</h3>
<ol>
<li><strong>App</strong>: The main component that orchestrates the entire application.</li>
<li><strong>Sidebar1</strong>: Manages chat history and category selection.</li>
<li><strong>Citation</strong>: Renders source citations for bot responses.</li>
<li><strong>RelatedQuestion</strong>: Displays related questions for further queries.</li>
<li><strong>CopyIcon</strong>: Provides copy-to-clipboard functionality.</li>
</ol>
<h3 id="utility-components">Utility Components</h3>
<ul>
<li><strong>StopIcon</strong>: Icon for stopping ongoing requests.</li>
<li><strong>SendIcon</strong>: Icon for sending messages.</li>
</ul>
<h2 id="state-management">State Management</h2>
<p>The app uses React&#39;s useState hook for managing various states:</p>
<ul>
<li><code>chats</code>: Stores all chat histories.</li>
<li><code>chatId</code>: Tracks the current active chat.</li>
<li><code>prompt</code>: Manages the current user input.</li>
<li><code>loading</code>: Indicates whether a response is being generated.</li>
<li><code>currentAnswer</code>: Stores the bot&#39;s current response.</li>
<li><code>category</code>: Manages the selected category (Finance or Oil &amp; Gas).</li>
</ul>
<h2 id="key-functionalities">Key Functionalities</h2>
<ol>
<li><p><strong>Chat Management</strong>:</p>
<ul>
<li>Start new chats</li>
<li>Rename existing chats</li>
<li>Delete chats</li>
</ul>
</li>
<li><p><strong>Message Handling</strong>:</p>
<ul>
<li>Send user messages</li>
<li>Receive and render bot responses</li>
<li>Handle markdown in bot responses</li>
</ul>
</li>
<li><p><strong>API Integration</strong>:</p>
<ul>
<li>Fetch responses from a backend API</li>
<li>Handle streaming responses</li>
</ul>
</li>
<li><p><strong>User Experience</strong>:</p>
<ul>
<li>Copy responses to clipboard</li>
<li>View and click on related questions</li>
<li>Access source citations</li>
</ul>
</li>
</ol>
<h2 id="setup-and-installation">Setup and Installation</h2>
<ol>
<li>Clone the repository</li>
<li>Install dependencies: <code>npm install</code></li>
<li>Start the development server: <code>npm run dev</code></li>
</ol>
<h2 id="configuration">Configuration</h2>
<p>Ensure that the backend API URL is correctly set in the <code>fetchData</code> function within <code>App.tsx</code>.</p>
<h2 id="usage">Usage</h2>
<ol>
<li>Select a category (Finance or Oil &amp; Gas)</li>
<li>Type your query in the input field</li>
<li>Press Enter or click the Send icon to submit</li>
<li>View the bot&#39;s response, including any citations or related questions</li>
<li>Click on citations to view sources</li>
<li>Use related questions for follow-up queries</li>
</ol>

