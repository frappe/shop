<template>
	<div class="inline-flex items-center gap-2">
		<template v-for="action in actions" :key="action.label">
			<Tooltip v-if="compact" :text="action.label">
				<Button
					variant="ghost"
					:theme="action.theme"
					:loading="action.run === approve && approving"
					@click="action.run()"
				>
					<template #icon><component :is="action.icon" class="size-4" /></template>
				</Button>
			</Tooltip>
			<Button
				v-else
				:theme="action.theme"
				:loading="action.run === approve && approving"
				@click="action.run()"
			>
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
import { Tooltip, call, toast } from 'frappe-ui'

import LucideCheck from '~icons/lucide/check'
import LucideCheckCheck from '~icons/lucide/check-check'
import LucideX from '~icons/lucide/x'

import ReturnStatusDialog from '@/components/ReturnStatusDialog.vue'

const props = defineProps<{ request: { name: string; status: string }; compact?: boolean }>()
const emit = defineEmits<{ updated: [] }>()

const approving = ref(false)
const showDialog = ref(false)
const dialogStatus = ref<'Rejected' | 'Completed'>('Rejected')

const actions = computed(() => {
	if (props.request.status === 'Requested') {
		return [
			{ label: 'Approve', theme: 'gray', icon: LucideCheck, run: approve },
			{ label: 'Reject', theme: 'red', icon: LucideX, run: () => openDialog('Rejected') },
		]
	}
	if (props.request.status === 'Approved') {
		return [
			{
				label: 'Mark completed',
				theme: 'gray',
				icon: LucideCheckCheck,
				run: () => openDialog('Completed'),
			},
		]
	}
	return []
})

function openDialog(status: 'Rejected' | 'Completed') {
	dialogStatus.value = status
	showDialog.value = true
}

async function approve() {
	approving.value = true
	try {
		await call('shop.api.returns.set_status', { name: props.request.name, status: 'Approved' })
		toast.success('Request approved')
		emit('updated')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not approve the request')
	} finally {
		approving.value = false
	}
}
</script>
