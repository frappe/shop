<template>
	<div class="flex items-center gap-1.5" data-shop="agent-typing">
		<span
			v-for="delay in [0, 150, 300]"
			:key="delay"
			class="size-1.5 animate-bounce rounded-full bg-ink-gray-4"
			:style="{ animationDelay: `${delay}ms` }"
		/>
		<span class="ml-1 text-sm text-ink-gray-5">Working on it</span>
	</div>
</template>
