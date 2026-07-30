<template>
	<div class="flex flex-col items-center py-10 text-center">
		<div class="flex size-11 items-center justify-center rounded-full bg-surface-gray-2">
			<LucideSparkles class="size-5 text-ink-gray-7" />
		</div>
		<h2 class="mt-4 text-lg font-semibold text-ink-gray-9">What should we do with the store?</h2>
		<p class="mt-1 max-w-md text-base leading-6 text-ink-gray-6">
			The assistant can read your catalogue, orders, stock and settings, and will ask before it
			changes anything.
		</p>
		<div class="mt-6 grid w-full gap-2 sm:grid-cols-2">
			<button
				v-for="prompt in prompts"
				:key="prompt"
				type="button"
				class="rounded-lg border border-outline-gray-2 bg-surface-white px-3.5 py-3 text-left text-base leading-6 text-ink-gray-7 transition hover:border-outline-gray-3 hover:bg-surface-gray-1"
				data-shop="agent-suggestion"
				@click="emit('pick', prompt)"
			>
				{{ prompt }}
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import LucideSparkles from '~icons/lucide/sparkles'

const emit = defineEmits<{ pick: [prompt: string] }>()

const prompts = [
	'How is the store doing this month?',
	'What still needs attention before I can sell?',
	'Add a product called Canvas Tote for ₹999 with 10 in stock',
	'Create a 15 percent coupon for this weekend',
]
</script>
