<script lang="ts">
	import '../app.css';
</script>

<div class="app">
	<header>
		<div class="container">
			<nav class="nav">
				<a href="/" class="logo">
					<h1>UFE Research Writer</h1>
				</a>
				<div class="nav-links">
					<a href="/">Sessions</a>
					<a href="/new">New Session</a>
				</div>
			</nav>
		</div>
	</header>

	<main>
		<slot />
	</main>
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	header {
		background: white;
		border-bottom: 1px solid var(--color-border);
		padding: 1rem 0;
	}

	.nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.logo h1 {
		font-size: 1.5rem;
		color: var(--color-primary);
	}

	.logo {
		text-decoration: none;
	}

	.nav-links {
		display: flex;
		gap: 1.5rem;
	}

	.nav-links a {
		text-decoration: none;
		color: var(--color-text);
		font-weight: 500;
		transition: color 0.2s;
	}

	.nav-links a:hover {
		color: var(--color-primary);
	}

	main {
		flex: 1;
		padding: 2rem 0;
	}
</style>
