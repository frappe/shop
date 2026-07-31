<template>
	<div>
		<button
			class="mb-2 inline-flex items-center gap-1 text-sm text-ink-gray-5 hover:text-ink-gray-8"
			@click="emit('back')"
		>
			<LucideArrowLeft class="size-3.5" />
			All walkthroughs
		</button>

		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-center gap-3">
				<h1 class="text-xl font-semibold text-ink-gray-9">{{ guide.title }}</h1>
				<Badge theme="gray">~{{ guide.minutes }} min</Badge>
				<Badge theme="gray">{{ guide.viewport }}</Badge>
			</div>
			<div class="flex items-center gap-2">
				<Button :loading="preparing" @click="emit('prepare')">
					<template #prefix><LucideRefreshCw class="size-4" /></template>
					Prepare again
				</Button>
				<Button variant="solid" @click="openStorefront">
					<template #prefix><LucideExternalLink class="size-4" /></template>
					Open storefront
				</Button>
			</div>
		</div>
		<p class="mt-1 text-base text-ink-gray-6">{{ guide.tagline }}</p>

		<p v-if="privateWindowTip" class="mt-3 text-sm text-ink-gray-6">
			Tip: use a private window so you start as a guest.
		</p>

		<div
			v-if="guide.prepared?.length"
			class="mt-6 rounded-lg border border-outline-green-1 bg-surface-green-1 p-4"
		>
			<div class="text-sm font-medium text-ink-green-3">Set up for you just now</div>
			<ul class="mt-2 space-y-1.5">
				<li v-for="note in guide.prepared" :key="note" class="flex items-start gap-2 text-sm text-ink-gray-7">
					<LucideCheck class="mt-0.5 size-4 shrink-0 text-ink-green-3" />
					<WalkthroughText :text="note" />
				</li>
			</ul>
		</div>

		<div v-if="guide.credentials" class="mt-4 rounded-lg border border-outline-gray-1 p-4">
			<div class="text-sm font-medium text-ink-gray-8">{{ guide.credentials.label }}</div>
			<dl class="mt-2 space-y-1.5">
				<div v-for="field in credentialFields" :key="field.label" class="flex items-center gap-2">
					<dt class="w-20 text-sm text-ink-gray-5">{{ field.label }}</dt>
					<dd class="font-mono text-sm text-ink-gray-8">{{ field.value }}</dd>
					<Tooltip :text="`Copy ${field.label.toLowerCase()}`">
						<Button variant="ghost" @click="copy(field)">
							<template #icon><LucideCopy class="size-3.5" /></template>
						</Button>
					</Tooltip>
				</div>
			</dl>
		</div>

		<h2 class="mt-8 text-base font-medium text-ink-gray-8">Steps</h2>
		<ul class="mt-3 space-y-2.5">
			<li v-for="(step, index) in guide.steps" :key="step" class="flex items-start gap-2.5">
				<Checkbox v-model="checked[index]" class="mt-0.5" />
				<span
					class="text-base"
					:class="checked[index] ? 'text-ink-gray-4 line-through' : 'text-ink-gray-7'"
				>
					<span class="mr-1 text-ink-gray-5">{{ index + 1 }}.</span>
					<WalkthroughText :text="step" />
				</span>
			</li>
		</ul>

		<h2 class="mt-8 text-base font-medium text-ink-gray-8">What should hold true</h2>
		<ul class="mt-3 space-y-1.5">
			<li v-for="point in guide.verify" :key="point" class="flex items-start gap-2 text-base text-ink-gray-7">
				<LucideShieldCheck class="mt-0.5 size-4 shrink-0 text-ink-gray-5" />
				{{ point }}
			</li>
		</ul>
	</div>
</template>

<script lang="ts">
export interface PersonaCredentials {
	label: string
	username: string
	password: string
}

export interface PersonaGuide {
	key: string
	title: string
	tagline: string
	kind: 'shopper' | 'merchant'
	minutes: number
	viewport: string
	start_url: string
	steps: string[]
	verify: string[]
	prepared?: string[]
	credentials?: PersonaCredentials | null
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Badge, Checkbox, Tooltip, toast } from 'frappe-ui'

import LucideArrowLeft from '~icons/lucide/arrow-left'
import LucideCheck from '~icons/lucide/check'
import LucideCopy from '~icons/lucide/copy'
import LucideExternalLink from '~icons/lucide/external-link'
import LucideRefreshCw from '~icons/lucide/refresh-cw'
import LucideShieldCheck from '~icons/lucide/shield-check'

import WalkthroughText from '@/components/WalkthroughText.vue'

const props = defineProps<{ guide: PersonaGuide; preparing: boolean }>()
const emit = defineEmits<{ back: []; prepare: [] }>()

const checked = ref<boolean[]>([])

watch(() => props.guide.key, () => (checked.value = props.guide.steps.map(() => false)), {
	immediate: true,
})

const privateWindowTip = computed(
	() =>
		props.guide.kind === 'shopper' &&
		!props.guide.steps.some((step) => step.toLowerCase().includes('private window')),
)

const credentialFields = computed(() => {
	const credentials = props.guide.credentials
	if (!credentials) return []
	return [
		{ label: 'Username', value: credentials.username },
		{ label: 'Password', value: credentials.password },
	]
})

function openStorefront() {
	window.open(props.guide.start_url, '_blank')
}

async function copy(field: { label: string; value: string }) {
	await navigator.clipboard.writeText(field.value)
	toast.success(`${field.label} copied`)
}
</script>
