<template>
	<Badge :theme="theme" variant="subtle">{{ label }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

const props = defineProps<{ label: string }>()

const themes: Record<string, string> = {
	Paid: 'green',
	Fulfilled: 'green',
	Completed: 'green',
	Converted: 'green',
	Unpaid: 'orange',
	'Partly fulfilled': 'orange',
	Abandoned: 'orange',
	Requested: 'orange',
	Approved: 'blue',
	Cancelled: 'red',
	Rejected: 'red',
	Draft: 'gray',
	Unfulfilled: 'gray',
}

const theme = computed(() => (themes[props.label] || 'blue') as any)
</script>
