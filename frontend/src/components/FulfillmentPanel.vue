<template>
	<section class="rounded-lg border border-outline-gray-1 p-4">
		<div class="flex items-center justify-between gap-3">
			<h2 class="text-base font-medium text-ink-gray-8">Fulfillment</h2>
			<FulfillmentStatusBadge v-if="shipment" :status="shipment.status" />
		</div>

		<div v-if="loading" class="mt-4 space-y-2">
			<div class="h-4 w-1/3 animate-pulse rounded bg-surface-gray-2" />
			<div class="h-4 w-2/3 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<div v-else-if="fulfillment.error" class="mt-4 flex flex-wrap items-center gap-3">
			<p class="text-base text-ink-red-8">{{ errorMessage }}</p>
			<Button @click="fulfillment.reload()">Try again</Button>
		</div>

		<template v-else-if="shipment">
			<dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
				<div>
					<dt class="text-sm text-ink-gray-5">Provider</dt>
					<dd class="text-base text-ink-gray-8">{{ shipment.provider_label }}</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">Reference</dt>
					<dd class="truncate text-base text-ink-gray-8">{{ shipment.external_id || 'Not set' }}</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">Carrier</dt>
					<dd class="text-base text-ink-gray-8">{{ shipment.carrier || 'Not set' }}</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">Tracking number</dt>
					<dd class="truncate text-base text-ink-gray-8">
						<a
							v-if="shipment.tracking_url"
							:href="shipment.tracking_url"
							target="_blank"
							class="inline-flex items-center gap-1 underline hover:text-ink-gray-9"
						>
							{{ shipment.tracking_number }}
							<LucideExternalLink class="size-3.5" />
						</a>
						<span v-else>{{ shipment.tracking_number || 'Not set' }}</span>
					</dd>
				</div>
			</dl>

			<p
				v-if="shipment.status === 'Failed' && shipment.error"
				class="mt-4 rounded bg-surface-red-1 px-3 py-2 text-sm text-ink-red-8"
			>
				{{ shipment.error }}
			</p>

			<dl v-if="timeline.length" class="mt-4 border-t border-outline-gray-1 pt-3 text-sm">
				<div v-for="event in timeline" :key="event.label" class="flex justify-between py-0.5">
					<dt class="text-ink-gray-5">{{ event.label }}</dt>
					<dd class="text-ink-gray-7">{{ event.on }}</dd>
				</div>
			</dl>

			<div class="mt-4 flex flex-wrap items-center gap-2">
				<Button v-if="canMarkShipped" variant="solid" @click="showShipDialog = true">
					Mark shipped
				</Button>
				<Button v-if="canResend" variant="solid" :loading="busy === 'send'" @click="send">
					Send to fulfillment
				</Button>
				<Button v-if="canRefresh" :loading="busy === 'sync'" @click="refresh">
					<template #prefix><LucideRefreshCw class="size-3.5" /></template>
					Refresh status
				</Button>
				<Button v-if="isOpen" theme="red" variant="ghost" @click="confirmCancel">
					Cancel shipment
				</Button>
			</div>
		</template>

		<template v-else>
			<p class="mt-3 text-base text-ink-gray-6">
				Nothing shipped yet. This order goes to
				<span class="font-medium text-ink-gray-8">{{ defaultProviderLabel }}</span>
				unless you pick another provider.
			</p>

			<p v-if="cancelled" class="mt-3 text-sm text-ink-gray-5">
				This order is cancelled, so it cannot be sent for fulfillment.
			</p>

			<div v-else class="mt-4 space-y-3">
				<FormControl
					v-if="providerOptions.length > 1"
					v-model="chosenKey"
					type="select"
					label="Provider"
					:options="providerOptions"
					class="max-w-xs"
				/>
				<p v-for="hint in setupHints" :key="hint" class="text-sm text-ink-gray-5">{{ hint }}</p>
				<Button
					variant="solid"
					:loading="busy === 'send'"
					:disabled="!chosenProvider?.configured"
					@click="send"
				>
					Send to fulfillment
				</Button>
			</div>
		</template>

		<FulfillmentShipDialog
			v-if="shipment"
			v-model="showShipDialog"
			:fulfillment="shipment.name"
			@shipped="afterAction"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { FormControl, call, createResource, dialog, toast } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'
import LucideRefreshCw from '~icons/lucide/refresh-cw'

import FulfillmentShipDialog from '@/components/FulfillmentShipDialog.vue'
import FulfillmentStatusBadge from '@/components/FulfillmentStatusBadge.vue'

export interface FulfillmentSummary {
	name: string
	sales_order: string
	provider: string
	provider_label: string
	status: string
	external_id?: string
	carrier?: string
	tracking_number?: string
	tracking_url?: string
	requested_on?: string
	shipped_on?: string
	delivered_on?: string
	error?: string
}

interface Provider {
	key: string
	label: string
	configured: boolean
	hint: string
}

const OPEN_STATUSES = ['Pending', 'Accepted', 'Shipped']

const props = defineProps<{ order: string; docstatus: number }>()
const emit = defineEmits<{ changed: [] }>()

const busy = ref('')
const chosenKey = ref('')
const showShipDialog = ref(false)

const fulfillment = createResource({
	url: 'shop.api.fulfillment.get_fulfillment',
	makeParams: () => ({ order: props.order }),
	auto: true,
})

const providers = createResource({
	url: 'shop.api.fulfillment.get_providers',
	auto: true,
})

// Only the "no shipment yet" state needs the store default, so it is fetched on demand.
const settings = createResource({ url: 'shop.api.settings.get_settings' })

const shipment = computed<FulfillmentSummary | null>(() => fulfillment.data || null)
const cancelled = computed(() => props.docstatus === 2)
const loading = computed(() => !fulfillment.fetched && !fulfillment.error)

watch(
	() => fulfillment.fetched,
	(fetched) => {
		if (fetched && !shipment.value && !settings.fetched) settings.fetch()
	},
)

const errorMessage = computed(() => {
	const error = fulfillment.error as { messages?: string[]; message?: string } | null
	return error?.messages?.[0] || error?.message || 'Could not load fulfillment details'
})

const providerList = computed<Provider[]>(() => providers.data || [])

const defaultProviderKey = computed(() => settings.data?.fulfillment_provider || 'manual')

const defaultProviderLabel = computed(
	() =>
		providerList.value.find((provider) => provider.key === defaultProviderKey.value)?.label ||
		defaultProviderKey.value,
)

const providerOptions = computed(() =>
	providerList.value.map((provider) => ({
		label: provider.configured ? provider.label : `${provider.label} (needs setup)`,
		value: provider.key,
		disabled: !provider.configured,
	})),
)

const setupHints = computed(() =>
	providerList.value
		.filter((provider) => !provider.configured && provider.hint)
		.map((provider) => `${provider.label}: ${provider.hint}`),
)

const chosenProvider = computed(
	() => providerList.value.find((provider) => provider.key === chosenKey.value) || null,
)

watch(
	[providerList, defaultProviderKey],
	() => {
		if (!chosenKey.value && providerList.value.length) chosenKey.value = defaultProviderKey.value
	},
	{ immediate: true },
)

const isOpen = computed(() => !!shipment.value && OPEN_STATUSES.includes(shipment.value.status))

const canMarkShipped = computed(
	() =>
		!!shipment.value &&
		shipment.value.provider === 'manual' &&
		['Pending', 'Accepted'].includes(shipment.value.status),
)

const canResend = computed(
	() =>
		!!shipment.value && !cancelled.value && ['Cancelled', 'Failed'].includes(shipment.value.status),
)

const canRefresh = computed(() => isOpen.value || shipment.value?.status === 'Delivered')

const timeline = computed(() => {
	const doc = shipment.value
	if (!doc) return []
	return [
		{ label: 'Requested', on: doc.requested_on },
		{ label: 'Shipped', on: doc.shipped_on },
		{ label: 'Delivered', on: doc.delivered_on },
	]
		.filter((event) => event.on)
		.map((event) => ({ label: event.label, on: formatStamp(event.on as string) }))
})

function formatStamp(value: string) {
	const parsed = new Date(value.replace(' ', 'T'))
	if (Number.isNaN(parsed.getTime())) return value
	return parsed.toLocaleString('en-GB', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	})
}

async function run(
	key: string,
	method: string,
	args: Record<string, any>,
	success: string,
	failure: string,
) {
	busy.value = key
	try {
		await call(method, args)
		toast.success(success)
		afterAction()
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || failure)
	} finally {
		busy.value = ''
	}
}

function afterAction() {
	fulfillment.reload()
	emit('changed')
}

function send() {
	run(
		'send',
		'shop.api.fulfillment.send_order',
		{ order: props.order, provider: chosenKey.value || undefined },
		'Order sent for fulfillment',
		'Could not send this order for fulfillment',
	)
}

function refresh() {
	if (!shipment.value) return
	run(
		'sync',
		'shop.api.fulfillment.sync_fulfillment',
		{ fulfillment: shipment.value.name },
		'Status refreshed',
		'Could not refresh the shipment status',
	)
}

function confirmCancel() {
	const doc = shipment.value
	if (!doc) return
	dialog.confirm({
		title: 'Cancel shipment',
		message: `Cancel this shipment with <b>${doc.provider_label}</b>? The order can be sent again.`,
		theme: 'red',
		confirmLabel: 'Cancel shipment',
		onConfirm: () =>
			run(
				'cancel',
				'shop.api.fulfillment.cancel_fulfillment',
				{ fulfillment: doc.name },
				'Shipment cancelled',
				'Could not cancel this shipment',
			),
	})
}
</script>
