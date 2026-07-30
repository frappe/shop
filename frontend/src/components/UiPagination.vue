<template>
	<div v-if="total > limit" class="flex items-center justify-between">
		<span class="text-sm text-ink-gray-5">
			Showing {{ start + 1 }}-{{ Math.min(start + limit, total) }} of {{ total }}
		</span>
		<div class="flex items-center gap-2">
			<Button :disabled="start === 0" @click="emit('update:start', Math.max(0, start - limit))">
				Previous
			</Button>
			<Button :disabled="start + limit >= total" @click="emit('update:start', start + limit)">
				Next
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	start: number
	limit: number
	total: number
}>()

const emit = defineEmits<{ 'update:start': [start: number] }>()
</script>
