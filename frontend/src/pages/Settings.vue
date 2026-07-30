<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<h1 class="text-xl font-semibold text-ink-gray-9">Settings</h1>

		<div class="mt-6 max-w-md space-y-4">
			<FormControl v-model="form.store_name" label="Store name" />
			<div>
				<FormControl v-model="form.allow_out_of_stock" type="checkbox" label="Allow out of stock orders" />
			</div>
			<div><FormControl v-model="form.prices_include_tax" type="checkbox" label="Prices include tax" /></div>
			<div><Button variant="solid" :loading="settings.setValue.loading" @click="save">Save</Button></div>
		</div>

		<div class="mt-10 max-w-md">
			<h2 class="text-lg font-medium text-ink-gray-8">Payments</h2>
			<p class="mt-1 text-base text-ink-gray-6">Choose how customers pay at checkout.</p>
			<div class="mt-4 rounded-lg border border-outline-gray-1 p-4">
				<Switch
					v-model="payments.enableCod"
					label="Cash on Delivery"
					description="Let customers pay in cash when their order arrives."
				/>
			</div>
			<div v-if="gatewayOptions.length > 1" class="mt-4">
				<FormControl
					v-model="payments.gatewayAccount"
					type="select"
					label="Online payment gateway"
					:options="gatewayOptions"
				/>
			</div>
			<p v-else class="mt-3 text-sm text-ink-gray-6">
				Connect Razorpay, Stripe, PayPal and more from payment settings. A connected gateway appears
				here automatically.
			</p>
			<div class="mt-4 flex items-center gap-4">
				<Button variant="solid" :loading="savingPayments" @click="savePayments">Save</Button>
				<a
					href="/app/payment-gateway-account"
					target="_blank"
					class="inline-flex items-center gap-1 text-sm text-ink-gray-6 underline hover:text-ink-gray-8"
				>
					Open payment settings in Desk
					<LucideExternalLink class="size-3.5" />
				</a>
			</div>
		</div>

		<div class="mt-10 max-w-md">
			<h2 class="text-lg font-medium text-ink-gray-8">Storefront</h2>
			<p class="mt-1 text-base text-ink-gray-6">Your storefront pages are built with Builder.</p>
			<div class="mt-4 flex items-center justify-between rounded-lg border border-outline-gray-1 p-4">
				<div>
					<div class="text-base font-medium text-ink-gray-9">Frappe</div>
					<div class="text-sm text-ink-gray-6">Active theme</div>
				</div>
				<Button @click="openBuilder">
					<template #prefix><LucideExternalLink class="size-3.5" /></template>
					Edit in Builder
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { FormControl, Switch, call, createDocumentResource, toast } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'

import { fetchOnboardingState, type GatewayAccount } from '@/stores/onboarding'

const form = reactive({
	store_name: '',
	allow_out_of_stock: false,
	prices_include_tax: false,
})

const payments = reactive({
	enableCod: true,
	gatewayAccount: '',
})

const gatewayAccounts = ref<GatewayAccount[]>([])
const savingPayments = ref(false)

const settings = createDocumentResource({
	doctype: 'Shop Settings',
	name: 'Shop Settings',
	auto: true,
})

watch(
	() => settings.doc,
	(doc) => {
		if (!doc) return
		form.store_name = doc.store_name || ''
		form.allow_out_of_stock = !!doc.allow_out_of_stock
		form.prices_include_tax = !!doc.prices_include_tax
	},
	{ immediate: true },
)

fetchOnboardingState(true).then((state) => {
	payments.enableCod = state.enable_cod !== 0
	payments.gatewayAccount = state.payment_gateway_account || ''
	gatewayAccounts.value = state.gateway_accounts
})

const gatewayOptions = computed(() => [
	{ label: 'No online gateway', value: '' },
	...gatewayAccounts.value.map((a) => ({
		label: `${a.payment_gateway} (${a.currency})`,
		value: a.name,
	})),
])

async function save() {
	try {
		await settings.setValue.submit({
			store_name: form.store_name,
			allow_out_of_stock: form.allow_out_of_stock ? 1 : 0,
			prices_include_tax: form.prices_include_tax ? 1 : 0,
		})
		toast.success('Settings saved')
	} catch (error) {
		toast.error('Could not save settings')
	}
}

async function savePayments() {
	savingPayments.value = true
	try {
		await call('shop.api.onboarding.update_payments', {
			enable_cod: payments.enableCod,
			payment_gateway_account: payments.gatewayAccount || null,
		})
		await fetchOnboardingState(true)
		toast.success('Payment settings saved')
	} catch (error) {
		toast.error('Could not save payment settings')
	} finally {
		savingPayments.value = false
	}
}

function openBuilder() {
	window.open('/builder', '_blank')
}
</script>
