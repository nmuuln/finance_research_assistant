<script lang="ts">
	import { onMount } from 'svelte';

	interface Session {
		id: string;
		topic: string;
		language: string;
		status: string;
		created_at: string;
		updated_at: string;
		artifact_count: number;
		file_count: number;
	}

	let sessions: Session[] = [];
	let loading = true;
	let error = '';

	onMount(async () => {
		await loadSessions();
	});

	async function loadSessions() {
		try {
			loading = true;
			const response = await fetch('/api/sessions');
			const data = await response.json();
			sessions = data.sessions || [];
		} catch (e) {
			error = 'Failed to load sessions';
			console.error(e);
		} finally {
			loading = false;
		}
	}

	function formatDate(dateString: string) {
		const date = new Date(dateString + (dateString.endsWith('Z') ? '' : 'Z')); // Ensure UTC
		return date.toLocaleString('en-US', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit',
			hour12: false
		});
	}
</script>

<svelte:head>
	<title>Sessions - UFE Research Writer</title>
</svelte:head>

<div class="container">
	<div class="header">
		<h1>Research Sessions</h1>
		<a href="/new" class="btn btn-primary">+ New Session</a>
	</div>

	{#if loading}
		<div class="loading-state">
			<div class="loading"></div>
			<p>Loading sessions...</p>
		</div>
	{:else if error}
		<div class="error-state">
			<p>{error}</p>
			<button class="btn btn-secondary" on:click={loadSessions}>Retry</button>
		</div>
	{:else if sessions.length === 0}
		<div class="empty-state">
			<h2>No sessions yet</h2>
			<p>Create your first research session to get started.</p>
			<a href="/new" class="btn btn-primary">Create Session</a>
		</div>
	{:else}
		<div class="sessions-grid">
			{#each sessions as session}
				<a href="/sessions/{session.id}" class="session-card">
					<div class="session-header">
						<h3>{session.topic || 'Untitled Session'}</h3>
						<span class="language-badge">{session.language.toUpperCase()}</span>
					</div>
					<div class="session-meta">
						<div class="meta-item">
							<span class="label">Artifacts:</span>
							<span class="value">{session.artifact_count || 0}</span>
						</div>
						<div class="meta-item">
							<span class="label">Files:</span>
							<span class="value">{session.file_count || 0}</span>
						</div>
					</div>
					<div class="session-footer">
						<span class="date">Updated: {formatDate(session.updated_at)}</span>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}

	.header h1 {
		font-size: 2rem;
	}

	.loading-state,
	.error-state,
	.empty-state {
		text-align: center;
		padding: 4rem 2rem;
	}

	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.empty-state h2 {
		margin-bottom: 0.5rem;
		color: var(--color-text-secondary);
	}

	.empty-state p {
		margin-bottom: 1.5rem;
		color: var(--color-text-secondary);
	}

	.sessions-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1.5rem;
	}

	.session-card {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 0.5rem;
		padding: 1.5rem;
		text-decoration: none;
		color: inherit;
		transition: all 0.2s;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.session-card:hover {
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
		border-color: var(--color-primary);
		transform: translateY(-2px);
	}

	.session-header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: 1rem;
	}

	.session-header h3 {
		font-size: 1.125rem;
		margin: 0;
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.language-badge {
		background: var(--color-primary);
		color: white;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.session-meta {
		display: flex;
		gap: 1.5rem;
	}

	.meta-item {
		display: flex;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.meta-item .label {
		color: var(--color-text-secondary);
	}

	.meta-item .value {
		font-weight: 600;
	}

	.session-footer {
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border);
	}

	.date {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}
</style>
