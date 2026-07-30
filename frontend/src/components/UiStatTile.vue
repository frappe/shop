<template>
	<div class="rounded-lg border border-outline-gray-1 p-4">
		<div class="text-sm text-ink-gray-5">{{ label }}</div>
		<div class="mt-1 text-xl font-semibold text-ink-gray-9">{{ value }}</div>
		<div v-if="hint" class="mt-0.5 text-sm text-ink-gray-5">{{ hint }}</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	label: string
	value: string | number
	hint?: string
}>()
</script>
