<template>
	<Badge :theme="theme" variant="subtle">{{ status }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

const props = defineProps<{ status: string }>()

const theme = computed(() => {
	if (props.status === 'Completed') return 'green'
	if (props.status === 'Cancelled') return 'red'
	if (props.status === 'Draft') return 'gray'
	return 'blue'
})
</script>
