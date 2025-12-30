<script lang="ts">
	import { goto } from '$app/navigation';

	let topic = '';
	let language = 'mn';
	let creating = false;
	let error = '';

	async function createSession() {
		if (!topic.trim()) {
			error = 'Please enter a research topic';
			return;
		}

		try {
			creating = true;
			error = '';

			const response = await fetch('/api/sessions', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ topic, language })
			});

			if (!response.ok) {
				throw new Error('Failed to create session');
			}

			const session = await response.json();
			goto(`/sessions/${session.id}`);
		} catch (e) {
			error = 'Failed to create session. Please try again.';
			console.error(e);
		} finally {
			creating = false;
		}
	}
</script>

<svelte:head>
	<title>New Session - UFE Research Writer</title>
</svelte:head>

<div class="container">
	<div class="form-container">
		<h1>Create New Research Session</h1>

		<form on:submit|preventDefault={createSession}>
			<div class="form-group">
				<label for="topic">Research Topic</label>
				<input
					id="topic"
					type="text"
					class="input"
					bind:value={topic}
					placeholder="e.g., Mongolia's sovereign credit rating outlook"
					required
				/>
				<p class="help-text">Enter a finance-related research question or topic</p>
			</div>

			<div class="form-group">
				<label for="language">Output Language</label>
				<select id="language" class="input" bind:value={language}>
					<option value="mn">Mongolian</option>
					<option value="en">English</option>
				</select>
			</div>

			{#if error}
				<div class="error-message">
					{error}
				</div>
			{/if}

			<div class="button-group">
				<button type="submit" class="btn btn-primary" disabled={creating}>
					{#if creating}
						<div class="loading"></div>
						Creating...
					{:else}
						Create Session
					{/if}
				</button>
				<a href="/" class="btn btn-secondary">Cancel</a>
			</div>
		</form>
	</div>
</div>

<style>
	.form-container {
		max-width: 600px;
		margin: 0 auto;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 2rem;
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	label {
		display: block;
		font-weight: 500;
		margin-bottom: 0.5rem;
	}

	.help-text {
		margin-top: 0.5rem;
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	select.input {
		cursor: pointer;
	}

	.error-message {
		padding: 0.75rem;
		background: #fee;
		border: 1px solid var(--color-error);
		border-radius: 0.375rem;
		color: var(--color-error);
		margin-bottom: 1rem;
	}

	.button-group {
		display: flex;
		gap: 1rem;
	}

	.btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		justify-content: center;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
