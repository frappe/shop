<template>
	<div v-if="total > 0" class="flex items-center justify-between py-3">
		<div class="text-sm text-ink-gray-6">Showing {{ from }} to {{ to }} of {{ total }}</div>
		<div class="flex gap-2">
			<Button :disabled="start === 0" @click="emit('update:start', Math.max(0, start - limit))">
				Previous
			</Button>
			<Button :disabled="to >= total" @click="emit('update:start', start + limit)">Next</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ start: number; limit: number; total: number }>()
const emit = defineEmits<{ 'update:start': [value: number] }>()

const from = computed(() => props.start + 1)
const to = computed(() => Math.min(props.start + props.limit, props.total))
</script>
