<template>
	<div class="inline-flex items-center gap-2">
		<template v-for="action in actions" :key="action.label">
			<Tooltip v-if="compact" :text="action.label">
				<Button variant="ghost" :theme="action.theme" @click="openDialog(action.status)">
					<template #icon><component :is="action.icon" class="size-4" /></template>
				</Button>
			</Tooltip>
			<Button v-else :theme="action.theme" @click="openDialog(action.status)">
				{{ action.label }}
			</Button>
		</template>

		<ReturnStatusDialog
			v-model="showDialog"
			:request="request.name"
			:status="dialogStatus"
			@updated="emit('updated')"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Tooltip } from 'frappe-ui'

import LucideCheck from '~icons/lucide/check'
import LucideCheckCheck from '~icons/lucide/check-check'
import LucideX from '~icons/lucide/x'

import ReturnStatusDialog, { type ResolutionStatus } from '@/components/ReturnStatusDialog.vue'

const props = defineProps<{ request: { name: string; status: string }; compact?: boolean }>()
const emit = defineEmits<{ updated: [] }>()

const showDialog = ref(false)
const dialogStatus = ref<ResolutionStatus>('Approved')

const actions = computed(() => {
	if (props.request.status === 'Requested') {
		return [
			{ label: 'Approve', theme: 'gray' as const, icon: LucideCheck, status: 'Approved' as const },
			{ label: 'Reject', theme: 'red' as const, icon: LucideX, status: 'Rejected' as const },
		]
	}
	if (props.request.status === 'Approved') {
		return [
			{
				label: 'Mark completed',
				theme: 'gray' as const,
				icon: LucideCheckCheck,
				status: 'Completed' as const,
			},
		]
	}
	return []
})

function openDialog(status: ResolutionStatus) {
	dialogStatus.value = status
	showDialog.value = true
}
</script>
