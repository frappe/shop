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
	'Partly shipped': 'orange',
	Abandoned: 'orange',
	Requested: 'orange',
	Waiting: 'orange',
	Approved: 'blue',
	Declined: 'red',
	'Can sign in': 'green',
	'Sign-in off': 'gray',
	'Staff login': 'gray',
	Cancelled: 'red',
	Rejected: 'red',
	Draft: 'gray',
	Unfulfilled: 'gray',
	Credited: 'gray',
}

const theme = computed(() => (themes[props.label] || 'blue') as any)
</script>
