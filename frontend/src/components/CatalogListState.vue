<template>
	<div v-if="loading" class="flex items-center justify-center py-20">
		<LoadingIndicator class="size-5 text-ink-gray-5" />
	</div>
	<div v-else-if="error" class="flex flex-col items-center gap-3 py-20 text-center">
		<p class="text-base text-ink-red-4">{{ errorMessage }}</p>
		<Button @click="emit('retry')">Try again</Button>
	</div>
	<div v-else-if="empty" class="flex flex-col items-center gap-1 py-20 text-center">
		<div class="text-base font-medium text-ink-gray-8">{{ emptyTitle }}</div>
		<div class="text-sm text-ink-gray-6">{{ emptySubtitle }}</div>
		<div class="mt-3"><slot name="action" /></div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { LoadingIndicator } from 'frappe-ui'

const props = defineProps<{
	loading?: boolean
	error?: unknown
	empty?: boolean
	emptyTitle: string
	emptySubtitle?: string
}>()

const emit = defineEmits<{ retry: [] }>()

const errorMessage = computed(() => {
	const error = props.error as { messages?: string[]; message?: string } | null
	return error?.messages?.[0] || error?.message || 'Something went wrong while loading this page.'
})
</script>
