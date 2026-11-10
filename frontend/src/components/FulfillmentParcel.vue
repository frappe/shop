<template>
	<div>
		<div v-if="title || shipment" class="flex items-center justify-between gap-3">
			<div v-if="title">
				<h3 class="text-sm font-medium text-ink-gray-8">{{ title }}</h3>
				<p class="text-p-sm text-ink-gray-5">{{ itemsLine }}</p>
			</div>
			<FulfillmentStatusBadge v-if="shipment" :status="shipment.status" class="ml-auto" />
		</div>

		<template v-if="shipment">
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

			<FulfillmentCourier
				v-if="shipment.courier"
				:fulfillment="shipment.name"
				:courier="shipment.courier"
				:open="isOpen"
				@changed="afterAction"
			/>

			<p
				v-if="shipment.status === 'Failed' && shipment.error"
				class="mt-4 rounded bg-surface-red-1 px-3 py-2 text-sm text-ink-red-8"
			>
				{{ shipment.error }}
			</p>

			<dl v-if="timeline.length" class="mt-4 border-t border-outline-gray-1 pt-3 text-sm">
				<div v-for="event in timeline" :key="event.label" class="flex justify-between py-0.5">
					<dt class="text-ink-gray-5">{{ event.label }}</dt>
					<dd class="text-ink-gray-7">{{ formatDateTime(event.on) }}</dd>
				</div>
			</dl>

			<div class="mt-4 flex flex-wrap items-center gap-2">
				<Button v-if="canMarkShipped" variant="solid" @click="showShipDialog = true">
					Mark shipped
				</Button>
				<Button v-if="canMarkReady" variant="solid" :loading="busy === 'ready'" @click="markReady">
					Ready to collect
				</Button>
				<Button v-if="canMarkDelivered" variant="solid" :loading="busy === 'delivered'" @click="markDelivered">
					{{ shipment?.provider === 'pickup' ? 'Collected' : 'Mark delivered' }}
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
			<p class="mt-3 text-p-base text-ink-gray-6">
				Nothing shipped yet. This parcel goes to
				<span class="font-medium text-ink-gray-8">{{ defaultProviderLabel }}</span>
				unless you pick another provider.
			</p>

			<p v-if="cancelled" class="mt-3 text-p-sm text-ink-gray-5">
				This order is cancelled, so it cannot be sent for fulfillment.
			</p>

			<div v-else class="mt-4 space-y-3">
				<FormControl
					v-if="providerOptions.length > 1"
					v-model="chosenKey"
					type="select"
					label="Provider"
					@update:model-value="picked = true"
					:options="providerOptions"
					class="max-w-xs"
				/>
				<p v-for="hint in setupHints" :key="hint" class="text-p-sm text-ink-gray-5">{{ hint }}</p>
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
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { FormControl, call, dialog, toast } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'
import LucideRefreshCw from '~icons/lucide/refresh-cw'

import FulfillmentCourier, { type Courier } from '@/components/FulfillmentCourier.vue'
import FulfillmentShipDialog from '@/components/FulfillmentShipDialog.vue'
import FulfillmentStatusBadge from '@/components/FulfillmentStatusBadge.vue'
import { formatDateTime } from '@/utils/format'

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
	courier?: Courier | null
}

export interface Parcel {
	warehouse: string | null
	warehouse_label: string | null
	provider: string
	provider_label: string
	items: { item_code: string; item_name: string; qty: number }[]
	fulfillment: FulfillmentSummary | null
}

interface Provider {
	key: string
	label: string
	configured: boolean
	hint: string
}

const OPEN_STATUSES = ['Pending', 'Accepted', 'Shipped']

const props = defineProps<{
	order: string
	docstatus: number
	parcel: Parcel
	providers: Provider[]
	title?: string
}>()
const emit = defineEmits<{ changed: [] }>()

const busy = ref('')
const chosenKey = ref('')
const picked = ref(false)
const showShipDialog = ref(false)

const shipment = computed<FulfillmentSummary | null>(() => props.parcel.fulfillment)
const cancelled = computed(() => props.docstatus === 2)
const itemsLine = computed(() =>
	props.parcel.items.map((item) => `${item.item_name} \u00d7 ${item.qty}`).join(', '),
)

const providerList = computed<Provider[]>(() => props.providers)

const defaultProviderKey = computed(() => props.parcel.provider || 'manual')

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

const setupHints = computed(() => {
	const provider = chosenProvider.value
	if (!provider || provider.configured || !provider.hint) return []
	return [`${provider.label}: ${provider.hint}`]
})

const chosenProvider = computed(
	() => providerList.value.find((provider) => provider.key === chosenKey.value) || null,
)

// the warehouse's provider, unless staff picked another
watch(
	[providerList, defaultProviderKey],
	() => {
		if (!picked.value && providerList.value.length) chosenKey.value = defaultProviderKey.value
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

const canMarkReady = computed(
	() =>
		!!shipment.value &&
		shipment.value.provider === 'pickup' &&
		['Pending', 'Accepted'].includes(shipment.value.status),
)

const canMarkDelivered = computed(
	() =>
		!!shipment.value &&
		['manual', 'pickup'].includes(shipment.value.provider) &&
		shipment.value.status === 'Shipped',
)

function markReady() {
	if (!shipment.value) return
	run(
		'ready',
		'shop.api.fulfillment.mark_shipped',
		{ fulfillment: shipment.value.name },
		'The customer has been told it is ready to collect',
		'Could not mark it ready to collect',
	)
}

function markDelivered() {
	if (!shipment.value) return
	run(
		'delivered',
		'shop.api.fulfillment.mark_delivered',
		{ fulfillment: shipment.value.name },
		shipment.value.provider === 'pickup' ? 'Marked collected' : 'Marked delivered',
		'Could not update the parcel',
	)
}

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
		.map((event) => ({ label: event.label, on: event.on as string }))
})

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
	emit('changed')
}

function send() {
	run(
		'send',
		'shop.api.fulfillment.send_order',
		{
			order: props.order,
			provider: chosenKey.value || undefined,
			warehouse: props.parcel.warehouse || undefined,
		},
		'Parcel sent for fulfillment',
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
		message: `Cancel this shipment with ${doc.provider_label}? The order can be sent again.`,
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
