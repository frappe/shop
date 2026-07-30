<template>
	<Badge :theme="theme" variant="subtle">{{ status }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

const props = defineProps<{ status: string }>()

const themes: Record<string, string> = {
	Shipped: 'green',
	Delivered: 'green',
	Cancelled: 'red',
	Failed: 'red',
}

const theme = computed(() => (themes[props.status] || 'gray') as any)
</script>
