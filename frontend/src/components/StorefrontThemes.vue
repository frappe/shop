<template>
	<div>
		<div v-if="themes.loading" class="text-p-sm text-ink-gray-5">Loading themes...</div>
		<div v-else class="grid gap-3 sm:grid-cols-2">
			<div
				v-for="theme in rows"
				:key="theme.group"
				class="overflow-hidden rounded-lg border"
				:class="theme.active ? 'border-outline-gray-4' : 'border-outline-gray-1'"
			>
				<img
					v-if="theme.preview"
					:src="theme.preview"
					:alt="theme.title"
					class="h-36 w-full border-b border-outline-gray-1 object-cover object-top"
				/>
				<div v-else class="flex h-36 items-center justify-center bg-surface-gray-2">
					<LucideLayoutTemplate class="size-5 text-ink-gray-4" />
				</div>
				<div class="flex items-start justify-between gap-3 p-3">
					<div class="min-w-0">
						<div class="flex items-center gap-2">
							<span class="text-base font-medium text-ink-gray-8">{{ theme.title }}</span>
							<Badge v-if="theme.active" theme="green" variant="subtle" label="Active" />
						</div>
						<p v-if="theme.description" class="mt-0.5 text-p-sm text-ink-gray-6">
							{{ theme.description }}
						</p>
					</div>
					<Button
						v-if="!theme.active"
						:loading="applying === theme.group"
						@click="confirm(theme)"
					>
						Apply
					</Button>
				</div>
			</div>
		</div>

		<Dialog v-model="showConfirm" :options="confirmOptions" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Badge, Dialog, call, createResource, toast } from 'frappe-ui'

import LucideLayoutTemplate from '~icons/lucide/layout-template'

interface Theme {
	group: string
	title: string
	description?: string
	preview?: string
	active: boolean
}

const emit = defineEmits<{ applied: [] }>()

const applying = ref('')
const showConfirm = ref(false)
const pending = ref<Theme | null>(null)

const themes = createResource({ url: 'shop.themes.list_themes', auto: true })
const rows = computed<Theme[]>(() => themes.data || [])

const confirmOptions = computed(() => ({
	title: `Switch to ${pending.value?.title || ''}`,
	message:
		'Your storefront pages will be rebuilt from this theme. Pages you edited in Builder are kept and restored if you switch back.',
	size: 'sm',
	actions: [{ label: 'Switch theme', variant: 'solid', onClick: apply }],
}))

function confirm(theme: Theme) {
	pending.value = theme
	showConfirm.value = true
}

async function apply() {
	const theme = pending.value
	if (!theme) return
	showConfirm.value = false
	applying.value = theme.group
	try {
		await call('shop.themes.apply_theme', { group: theme.group })
		toast.success(`${theme.title} is live on your storefront`)
		themes.reload()
		emit('applied')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not switch the theme')
	} finally {
		applying.value = ''
	}
}
</script>
