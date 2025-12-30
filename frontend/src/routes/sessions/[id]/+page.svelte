<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, tick } from 'svelte';
	import { marked } from 'marked';

	interface Message {
		id?: number;
		role: 'user' | 'assistant';
		content: string;
		created_at?: string;
		metadata?: any;
	}

	interface Artifact {
		id: number;
		title: string;
		content: string;
		created_at: string;
		file_url: string;
		research_brief: string;
		reference_list: string;
	}

	interface UploadedFile {
		id: number;
		filename: string;
		file_type: string;
		file_size: number;
		uploaded_at: string;
		processed: boolean;
		storage_path: string;
		file_url?: string;
		extracted_content?: string;
	}

	interface Session {
		id: string;
		topic: string;
		language: string;
		status: string;
		created_at: string;
	}

	let sessionId = $page.params.id;
	let session: Session | null = null;
	let messages: Message[] = [];
	let artifacts: Artifact[] = [];
	let files: UploadedFile[] = [];
	let selectedArtifact: Artifact | null = null;

	let loading = true;
	let sending = false;
	let inputMessage = '';
	let showArtifacts = true;
	let sidebarView: 'artifacts' | 'files' = 'artifacts'; // Toggle between artifacts and files
	let fileInput: HTMLInputElement;
	let messagesContainer: HTMLDivElement;
	let inputElement: HTMLTextAreaElement;

	// Agent state
	let agentThinking = false;
	let thinkingMessage = '';

	onMount(async () => {
		await loadSession();
		scrollToBottom();
		// Auto-focus the input box
		await tick();
		focusInput();
	});

	function focusInput() {
		if (inputElement && !sending) {
			inputElement.focus();
		}
	}

	async function loadSession() {
		try {
			loading = true;
			const response = await fetch(`/api/sessions/${sessionId}`);
			const data = await response.json();

			session = data.session;
			artifacts = data.artifacts || [];
			files = data.files || [];
			messages = data.messages || [];

			// No welcome message - clean start like ADK

			// Auto-select first artifact if available
			if (artifacts.length > 0 && !selectedArtifact) {
				selectedArtifact = artifacts[0];
			}
		} catch (e) {
			console.error('Failed to load session:', e);
		} finally {
			loading = false;
		}
	}

	async function sendMessage() {
		if (!inputMessage.trim() || sending) return;

		const userMessage: Message = {
			role: 'user',
			content: inputMessage,
			created_at: new Date().toISOString()
		};

		messages = [...messages, userMessage];
		const userInput = inputMessage;
		inputMessage = '';

		await tick();
		scrollToBottom();

		try {
			sending = true;
			agentThinking = true;
			thinkingMessage = 'Thinking...';

			// Call ADK agent endpoint
			const response = await fetch(`/api/sessions/${sessionId}/agent-chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: userInput })
			});

			if (!response.ok) {
				throw new Error('Agent chat failed');
			}

			const data = await response.json();

			const assistantMessage: Message = {
				role: 'assistant',
				content: data.content,
				created_at: new Date().toISOString()
			};

			messages = [...messages, assistantMessage];

			await tick();
			scrollToBottom();
		} catch (e) {
			console.error('Send message failed:', e);
			messages = [
				...messages,
				{
					role: 'assistant',
					content: '❌ Sorry, I encountered an error. Please try again.',
					created_at: new Date().toISOString()
				}
			];
		} finally {
			sending = false;
			agentThinking = false;
			// Refocus input after sending
			await tick();
			focusInput();
		}
	}


	async function handleFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];

		if (!file) return;

		try {
			// Show uploading message
			messages = [
				...messages,
				{
					role: 'user',
					content: `📎 Uploading file: ${file.name}`,
					created_at: new Date().toISOString()
				}
			];

			await tick();
			scrollToBottom();

			agentThinking = true;
			thinkingMessage = 'Processing file...';

			const formData = new FormData();
			formData.append('file', file);

			const response = await fetch(`/api/sessions/${sessionId}/upload`, {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error('Upload failed');
			}

			const result = await response.json();

			// Reload session to get new file
			await loadSession();

			messages = [
				...messages,
				{
					role: 'assistant',
					content: `✅ File uploaded successfully!

**File:** ${result.filename}
**Size:** ${formatFileSize(result.file_size)}
**Status:** ${result.processed ? 'Processed ✓' : 'Processing...'}

${result.processed ? "I've analyzed the content and it will be included in future research." : "I'm analyzing the content now. It will be ready shortly."}`,
					created_at: new Date().toISOString()
				}
			];

			input.value = '';
			await tick();
			scrollToBottom();
		} catch (e) {
			messages = [
				...messages,
				{
					role: 'assistant',
					content: `❌ File upload failed: ${e}

Please ensure the file is a PDF, Excel, or CSV format.`,
					created_at: new Date().toISOString()
				}
			];
		} finally {
			agentThinking = false;
		}
	}

	function formatFileSize(bytes: number) {
		if (bytes < 1024) return bytes + ' B';
		if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
		return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
	}

	function formatDate(dateString: string) {
		// Ensure UTC timestamp is properly handled
		const date = new Date(dateString + (dateString.endsWith('Z') ? '' : 'Z'));
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(diff / 3600000);
		const days = Math.floor(diff / 86400000);

		if (minutes < 1) return 'Just now';
		if (minutes < 60) return `${minutes}m ago`;
		if (hours < 24) return `${hours}h ago`;
		if (days < 7) return `${days}d ago`;
		// Show full date in local timezone for older messages
		return date.toLocaleString('en-US', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			hour12: false
		});
	}

	function scrollToBottom() {
		setTimeout(() => {
			if (messagesContainer) {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}
		}, 100);
	}

	function handleKeyPress(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	function selectArtifact(artifact: Artifact) {
		selectedArtifact = artifact;
		showArtifacts = true;
	}

	function downloadFile(file: UploadedFile) {
		if (file.file_url) {
			// Open file in new tab to download
			window.open(file.file_url, '_blank');
		} else {
			// Fallback: try to construct URL from storage_path
			console.error('No file URL available for:', file.filename);
		}
	}

	$: artifactHtml = selectedArtifact ? marked(selectedArtifact.content) : '';
</script>

<svelte:head>
	<title>{session?.topic || 'Session'} - UFE Research Writer</title>
</svelte:head>

{#if loading}
	<div class="loading-screen">
		<div class="loading"></div>
		<p>Loading session...</p>
	</div>
{:else if !session}
	<div class="error-screen">
		<h2>Session not found</h2>
		<a href="/" class="btn btn-primary">← Go Home</a>
	</div>
{:else}
	<div class="chat-layout">
		<!-- Main Chat Area -->
		<div class="chat-main">
			<!-- Header -->
			<div class="chat-header">
				<div class="header-left">
					<a href="/" class="back-btn">←</a>
					<div>
						<h1>{session.topic || 'Untitled Session'}</h1>
						<div class="header-meta">
							<span class="lang-badge">{session.language.toUpperCase()}</span>
							{#if files.length > 0}
								<span class="file-count">📎 {files.length} file{files.length > 1 ? 's' : ''}</span>
							{/if}
						</div>
					</div>
				</div>
				<button class="toggle-artifacts" on:click={() => (showArtifacts = !showArtifacts)}>
					{showArtifacts ? '→' : '←'} Resources ({artifacts.length + files.length})
				</button>
			</div>

			<!-- Messages -->
			<div class="messages" bind:this={messagesContainer}>
				{#if messages.length === 0}
					<div class="empty-chat">
						<div class="empty-icon">💬</div>
						<h3>Start a conversation</h3>
						<p>Ask me to research a topic, upload files, or generate a report</p>
						<div class="starter-prompts">
							<button class="starter-prompt" on:click={() => inputMessage = "Run research on " + session.topic}>
								Research {session.topic}
							</button>
							<button class="starter-prompt" on:click={() => inputMessage = "How do I upload files?"}>
								Upload research materials
							</button>
							<button class="starter-prompt" on:click={() => inputMessage = "Generate a report"}>
								Generate a thesis report
							</button>
						</div>
					</div>
				{/if}
				{#each messages as message}
					<div class="message {message.role}">
						<div class="message-avatar">
							{#if message.role === 'assistant'}
								<div class="avatar-assistant">🤖</div>
							{:else}
								<div class="avatar-user">👤</div>
							{/if}
						</div>
						<div class="message-content">
							<div class="message-header">
								<span class="message-role"
									>{message.role === 'assistant' ? 'Research Agent' : 'You'}</span
								>
								{#if message.created_at}
									<span class="message-time">{formatDate(message.created_at)}</span>
								{/if}
							</div>
							<div class="message-text">
								{@html marked(message.content)}
							</div>
						</div>
					</div>
				{/each}

				{#if agentThinking}
					<div class="message assistant thinking">
						<div class="message-avatar">
							<div class="avatar-assistant">🤖</div>
						</div>
						<div class="message-content">
							<div class="message-header">
								<span class="message-role">Research Agent</span>
							</div>
							<div class="message-text">
								<div class="typing-indicator">
									<span></span>
									<span></span>
									<span></span>
								</div>
								<span class="thinking-text">{thinkingMessage}</span>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Input Area -->
			<div class="input-area">
				<button class="attach-btn" on:click={() => fileInput.click()} title="Upload file">
					📎
				</button>
				<input
					type="file"
					bind:this={fileInput}
					on:change={handleFileSelect}
					accept=".pdf,.csv,.xls,.xlsx"
					style="display: none;"
				/>
				<textarea
					bind:this={inputElement}
					bind:value={inputMessage}
					on:keypress={handleKeyPress}
					placeholder="Type a message... (Shift+Enter for new line)"
					rows="1"
					disabled={sending}
				></textarea>
				<button class="send-btn" on:click={sendMessage} disabled={sending || !inputMessage.trim()}>
					{#if sending}
						<div class="loading small"></div>
					{:else}
						↑
					{/if}
				</button>
			</div>
		</div>

		<!-- Artifacts Sidebar -->
		{#if showArtifacts}
			<div class="artifacts-sidebar">
				<div class="sidebar-header">
					<div class="sidebar-tabs">
					<button
						class="tab-btn"
						class:active={sidebarView === 'artifacts'}
						on:click={() => (sidebarView = 'artifacts')}
					>
						Artifacts ({artifacts.length})
					</button>
					<button
						class="tab-btn"
						class:active={sidebarView === 'files'}
						on:click={() => (sidebarView = 'files')}
					>
						Files ({files.length})
					</button>
				</div>
					<button class="close-sidebar" on:click={() => (showArtifacts = false)}>×</button>
				</div>

				{#if sidebarView === 'artifacts'}
				{#if artifacts.length === 0}
					<div class="empty-artifacts">
						<p>No reports yet</p>
						<small>Ask me to generate a report!</small>
					</div>
				{:else}
					<div class="artifacts-list">
						{#each artifacts as artifact}
							<button
								class="artifact-item"
								class:selected={selectedArtifact?.id === artifact.id}
								on:click={() => selectArtifact(artifact)}
							>
								<div class="artifact-icon">📄</div>
								<div class="artifact-info">
									<div class="artifact-title">{artifact.title}</div>
									<div class="artifact-date">{formatDate(artifact.created_at)}</div>
								</div>
							</button>
						{/each}
					</div>

					{#if selectedArtifact}
						<div class="artifact-viewer">
							<div class="viewer-header">
								<h4>{selectedArtifact.title}</h4>
								{#if selectedArtifact.file_url}
									<a
										href={selectedArtifact.file_url}
										target="_blank"
										class="download-btn"
										title="Download Word document"
									>
										📥
									</a>
								{/if}
							</div>
							<div class="viewer-content">
								{@html artifactHtml}
							</div>
						</div>
					{/if}
				{/if}
			{:else}
				<!-- Files View -->
				{#if files.length === 0}
					<div class="empty-artifacts">
						<p>No files uploaded yet</p>
						<small>Use the 📎 button to upload files</small>
					</div>
				{:else}
					<div class="files-list">
						{#each files as file}
							<button
								class="file-item"
								on:click={() => downloadFile(file)}
								title="Click to download {file.filename}"
							>
								<div class="file-icon">
									{#if file.file_type.includes('pdf')}
										📄
									{:else if file.file_type.includes('excel') || file.file_type.includes('spreadsheet')}
										📊
									{:else if file.file_type.includes('csv')}
										📋
									{:else}
										📎
									{/if}
								</div>
								<div class="file-info">
									<div class="file-name">{file.filename}</div>
									<div class="file-meta">
										<span class="file-size">{formatFileSize(file.file_size)}</span>
										<span class="file-dot">•</span>
										<span class="file-date">{formatDate(file.uploaded_at)}</span>
									</div>
									<div class="file-status">
										{#if file.processed}
											<span class="status-badge processed">✓ Processed</span>
										{:else}
											<span class="status-badge processing">⏳ Processing</span>
										{/if}
									</div>
								</div>
								<div class="download-icon">📥</div>
							</button>
						{/each}
					</div>
				{/if}
			{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.loading-screen,
	.error-screen {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 80vh;
		gap: 1rem;
	}

	.chat-layout {
		display: flex;
		height: calc(100vh - 80px);
		background: var(--color-bg);
		position: relative;
	}

	.chat-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		background: white;
		position: relative;
	}

	.chat-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid var(--color-border);
		background: white;
		flex-shrink: 0;
		position: sticky;
		top: 0;
		z-index: 5;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.back-btn {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: var(--color-bg-secondary);
		text-decoration: none;
		font-size: 1.25rem;
		color: var(--color-text);
		transition: background 0.2s;
	}

	.back-btn:hover {
		background: var(--color-border);
	}

	.chat-header h1 {
		font-size: 1.25rem;
		margin: 0;
	}

	.header-meta {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.25rem;
		font-size: 0.875rem;
	}

	.lang-badge {
		background: var(--color-primary);
		color: white;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.file-count {
		color: var(--color-text-secondary);
	}

	.toggle-artifacts {
		padding: 0.5rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		background: white;
		cursor: pointer;
		font-size: 0.875rem;
		transition: all 0.2s;
	}

	.toggle-artifacts:hover {
		background: var(--color-bg-secondary);
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 1.5rem;
		padding-bottom: 2rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		min-height: 0;
	}

	.empty-chat {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 2rem;
		max-width: 600px;
		margin: 0 auto;
	}

	.empty-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
		opacity: 0.5;
	}

	.empty-chat h3 {
		font-size: 1.5rem;
		margin-bottom: 0.5rem;
		color: var(--color-text);
	}

	.empty-chat p {
		color: var(--color-text-secondary);
		margin-bottom: 2rem;
		font-size: 1rem;
	}

	.starter-prompts {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		width: 100%;
		max-width: 400px;
	}

	.starter-prompt {
		padding: 1rem 1.5rem;
		border: 1px solid var(--color-border);
		border-radius: 0.5rem;
		background: white;
		cursor: pointer;
		font-size: 0.9375rem;
		text-align: left;
		transition: all 0.2s;
		color: var(--color-text);
	}

	.starter-prompt:hover {
		border-color: var(--color-primary);
		background: var(--color-bg-secondary);
		transform: translateY(-2px);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	}

	.message {
		display: flex;
		gap: 0.75rem;
		animation: fadeIn 0.3s ease-in;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.message-avatar {
		flex-shrink: 0;
	}

	.avatar-assistant,
	.avatar-user {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
	}

	.avatar-assistant {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	}

	.avatar-user {
		background: var(--color-bg-secondary);
	}

	.message-content {
		flex: 1;
		max-width: 800px;
	}

	.message-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.message-role {
		font-weight: 600;
		font-size: 0.875rem;
	}

	.message-time {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.message-text {
		line-height: 1.6;
		color: var(--color-text);
	}

	.message-text :global(h1),
	.message-text :global(h2),
	.message-text :global(h3) {
		margin-top: 1rem;
		margin-bottom: 0.5rem;
	}

	.message-text :global(p) {
		margin-bottom: 0.75rem;
	}

	.message-text :global(ul),
	.message-text :global(ol) {
		margin-left: 1.5rem;
		margin-bottom: 0.75rem;
	}

	.message-text :global(code) {
		background: var(--color-bg-secondary);
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-size: 0.875em;
	}

	.message-text :global(strong) {
		font-weight: 600;
		color: var(--color-text);
	}

	.message-text :global(a) {
		color: var(--color-primary);
		text-decoration: none;
	}

	.message-text :global(a:hover) {
		text-decoration: underline;
	}

	.typing-indicator {
		display: inline-flex;
		gap: 0.25rem;
		margin-right: 0.5rem;
	}

	.typing-indicator span {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--color-primary);
		animation: bounce 1.4s infinite ease-in-out both;
	}

	.typing-indicator span:nth-child(1) {
		animation-delay: -0.32s;
	}

	.typing-indicator span:nth-child(2) {
		animation-delay: -0.16s;
	}

	@keyframes bounce {
		0%,
		80%,
		100% {
			transform: scale(0);
			opacity: 0.5;
		}
		40% {
			transform: scale(1);
			opacity: 1;
		}
	}

	.thinking-text {
		color: var(--color-text-secondary);
		font-style: italic;
	}

	.input-area {
		display: flex;
		gap: 0.75rem;
		padding: 1rem 1.5rem;
		border-top: 1px solid var(--color-border);
		background: white;
		align-items: flex-end;
		flex-shrink: 0;
		position: sticky;
		bottom: 0;
		z-index: 5;
		box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
	}

	.attach-btn {
		width: 40px;
		height: 40px;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		background: white;
		cursor: pointer;
		font-size: 1.25rem;
		transition: all 0.2s;
		flex-shrink: 0;
	}

	.attach-btn:hover {
		background: var(--color-bg-secondary);
	}

	.input-area textarea {
		flex: 1;
		min-height: 40px;
		max-height: 200px;
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		font-family: inherit;
		font-size: 0.9375rem;
		resize: none;
		line-height: 1.5;
	}

	.input-area textarea:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.send-btn {
		width: 40px;
		height: 40px;
		border: none;
		border-radius: 0.375rem;
		background: var(--color-primary);
		color: white;
		cursor: pointer;
		font-size: 1.25rem;
		font-weight: bold;
		transition: all 0.2s;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.send-btn:hover:not(:disabled) {
		background: var(--color-primary-hover);
	}

	.send-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.artifacts-sidebar {
		width: 400px;
		border-left: 1px solid var(--color-border);
		background: var(--color-bg-secondary);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.sidebar-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid var(--color-border);
		background: white;
	}

	.sidebar-header h3 {
		font-size: 1rem;
		margin: 0;
	}

	.sidebar-tabs {
		display: flex;
		gap: 0.5rem;
	}

	.tab-btn {
		padding: 0.5rem 0.75rem;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text-secondary);
		border-bottom: 2px solid transparent;
		transition: all 0.2s;
	}

	.tab-btn:hover {
		color: var(--color-text);
	}

	.tab-btn.active {
		color: var(--color-primary);
		border-bottom-color: var(--color-primary);
	}

	.close-sidebar {
		width: 28px;
		height: 28px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 1.5rem;
		line-height: 1;
		color: var(--color-text-secondary);
	}

	.empty-artifacts {
		padding: 3rem 1.5rem;
		text-align: center;
		color: var(--color-text-secondary);
	}

	.artifacts-list {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-height: 200px;
		overflow-y: auto;
	}

	.artifact-item {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		border: 2px solid transparent;
		border-radius: 0.375rem;
		background: white;
		cursor: pointer;
		text-align: left;
		transition: all 0.2s;
	}

	.artifact-item:hover {
		border-color: var(--color-border);
	}

	.artifact-item.selected {
		border-color: var(--color-primary);
		background: #eff6ff;
	}

	.artifact-icon {
		font-size: 1.5rem;
	}

	.artifact-info {
		flex: 1;
		min-width: 0;
	}

	.artifact-title {
		font-weight: 500;
		font-size: 0.875rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.artifact-date {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin-top: 0.125rem;
	}

	.artifact-viewer {
		flex: 1;
		display: flex;
		flex-direction: column;
		background: white;
		margin: 0 1rem 1rem;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.viewer-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--color-border);
	}

	.viewer-header h4 {
		font-size: 0.875rem;
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.download-btn {
		font-size: 1.25rem;
		text-decoration: none;
		opacity: 0.7;
		transition: opacity 0.2s;
	}

	.download-btn:hover {
		opacity: 1;
	}

	.viewer-content {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		font-size: 0.875rem;
		line-height: 1.6;
	}

	.viewer-content :global(h1) {
		font-size: 1.25rem;
		margin-bottom: 0.75rem;
	}

	.viewer-content :global(h2) {
		font-size: 1.125rem;
		margin-top: 1.5rem;
		margin-bottom: 0.5rem;
	}

	.viewer-content :global(h3) {
		font-size: 1rem;
		margin-top: 1rem;
		margin-bottom: 0.5rem;
	}

	.viewer-content :global(p) {
		margin-bottom: 0.75rem;
	}

	.viewer-content :global(ul),
	.viewer-content :global(ol) {
		margin-left: 1.5rem;
		margin-bottom: 0.75rem;
	}

	.files-list {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		overflow-y: auto;
	}

	.file-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		transition: all 0.2s;
		cursor: pointer;
		width: 100%;
		text-align: left;
		position: relative;
	}

	.file-item:hover {
		border-color: var(--color-primary);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		transform: translateY(-1px);
	}

	.file-item:active {
		transform: translateY(0);
	}

	.file-icon {
		font-size: 2rem;
		flex-shrink: 0;
	}

	.file-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.file-name {
		font-weight: 500;
		font-size: 0.875rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--color-text);
	}

	.file-meta {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.file-dot {
		color: var(--color-border);
	}

	.file-status {
		display: flex;
		align-items: center;
	}

	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.status-badge.processed {
		background: #dcfce7;
		color: #166534;
	}

	.status-badge.processing {
		background: #fef3c7;
		color: #92400e;
	}

	.download-icon {
		font-size: 1.25rem;
		opacity: 0.5;
		transition: opacity 0.2s;
		flex-shrink: 0;
		margin-left: auto;
	}

	.file-item:hover .download-icon {
		opacity: 1;
	}

	@media (max-width: 1024px) {
		.artifacts-sidebar {
			position: absolute;
			right: 0;
			top: 0;
			bottom: 0;
			z-index: 10;
			box-shadow: -4px 0 6px rgba(0, 0, 0, 0.1);
		}
	}

	.loading.small {
		width: 20px;
		height: 20px;
		border-width: 2px;
	}
</style>
