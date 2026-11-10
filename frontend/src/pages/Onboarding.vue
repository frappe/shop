<template>
	<div class="min-h-screen bg-surface-base">
		<div class="mx-auto max-w-xl px-6 py-14">
			<div class="mb-10 flex items-center justify-center gap-3">
				<template v-for="(label, index) in stepLabels" :key="label">
					<div class="flex items-center gap-2">
						<span
							class="flex size-6 items-center justify-center rounded-full text-sm"
							:class="
								step > index + 1
									? 'bg-surface-gray-7 text-ink-white'
									: step === index + 1
										? 'bg-surface-gray-7 text-ink-white'
										: 'bg-surface-gray-2 text-ink-gray-5'
							"
						>
							<LucideCheck v-if="step > index + 1" class="size-3.5" />
							<template v-else>{{ index + 1 }}</template>
						</span>
						<span class="text-base" :class="step === index + 1 ? 'text-ink-gray-9' : 'text-ink-gray-5'">
							{{ label }}
						</span>
					</div>
					<div v-if="index < stepLabels.length - 1" class="h-px w-10 bg-outline-gray-2" />
				</template>
			</div>

			<div v-if="step === 1">
				<h1 class="text-xl font-semibold text-ink-gray-9">First, let's name your store</h1>
				<p class="mt-1 text-p-base text-ink-gray-6">
					This is what customers will see. You can always change it later.
				</p>
				<FormControl
					v-model="storeName"
					class="mt-6"
					label="Store name"
					placeholder="Acme Outfitters"
					required
					@keyup.enter="saveStore"
				/>
				<Button
					class="mt-6 w-full"
					variant="solid"
					:disabled="!storeName.trim()"
					:loading="savingStore"
					@click="saveStore"
				>
					Continue
				</Button>
			</div>

			<div v-else-if="step === 2">
				<h1 class="text-xl font-semibold text-ink-gray-9">Add your first products</h1>
				<p class="mt-1 text-p-base text-ink-gray-6">
					Products are what you sell. Add your own from the Products page, or load samples to try the store
					out first.
				</p>
				<div class="mt-6 rounded-lg border border-outline-gray-1 p-4">
					<Switch
						v-model="loadSamples"
						label="Load sample products"
						description="Adds a small demo catalog, published on your storefront. You can remove it from the Products page."
					/>
				</div>
				<p class="mt-3 text-p-sm text-ink-gray-5">
					You can add, edit, or remove products anytime from the Products page.
				</p>
				<div class="mt-6 flex gap-2">
					<Button class="w-1/3" @click="step = 1">Back</Button>
					<Button class="flex-1" variant="solid" :loading="loadingSamples" @click="saveProducts">
						Continue
					</Button>
				</div>
			</div>

			<div v-else>
				<h1 class="text-xl font-semibold text-ink-gray-9">Set up payments</h1>
				<p class="mt-1 text-p-base text-ink-gray-6">Choose how customers pay at checkout.</p>
				<div class="mt-6 rounded-lg border border-outline-gray-1 p-4">
					<Switch
						v-model="enableCod"
						label="Cash on Delivery"
						description="Let customers pay in cash when their order arrives."
					/>
				</div>
				<div v-if="gatewayNames.length" class="mt-4 flex flex-col gap-3">
					<Switch
						v-for="gateway in gatewayNames"
						:key="gateway"
						:model-value="chosenGateways.includes(gateway)"
						:label="gateway"
						description="Customers can pay online through this gateway. Set its label and fee in Settings."
						@update:model-value="(on: boolean) => toggleGateway(gateway, on)"
					/>
				</div>
				<div v-else class="mt-4 rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-4">
					<div class="text-base font-medium text-ink-gray-8">Accept online payments</div>
					<p class="mt-1 text-p-sm text-ink-gray-6">
						Set up Stripe, PayPal, Razorpay and more under Payment Gateways in Desk. A gateway set up
						there appears here automatically.
					</p>
					<a
						href="/app/payment-gateway"
						target="_blank"
						class="mt-2 inline-flex items-center gap-1 text-sm text-ink-gray-7 underline hover:text-ink-gray-9"
					>
						Open Payment Gateways
						<LucideExternalLink class="size-3.5" />
					</a>
				</div>
				<div class="mt-6 flex gap-2">
					<Button class="w-1/3" @click="step = 2">Back</Button>
					<Button class="flex-1" variant="solid" :loading="finishing" @click="finish">Finish</Button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { FormControl, Switch, call, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideCheck from '~icons/lucide/check'
import LucideExternalLink from '~icons/lucide/external-link'

import { fetchOnboardingState, type GatewayAccount } from '@/stores/onboarding'

const router = useRouter()
const stepLabels = ['Store details', 'Add products', 'Payments']

const step = ref(1)
const storeName = ref('')
const loadSamples = ref(false)
const enableCod = ref(true)
const chosenGateways = ref<string[]>([])
const gatewayAccounts = ref<GatewayAccount[]>([])
const savingStore = ref(false)
const loadingSamples = ref(false)
const finishing = ref(false)

fetchOnboardingState().then((state) => {
	storeName.value = state.store_name || ''
	enableCod.value = state.enable_cod !== 0
	gatewayAccounts.value = state.gateway_accounts
	chosenGateways.value = state.payment_gateways.length
		? [...state.payment_gateways]
		: state.gateway_accounts.filter((a) => a.is_default).map((a) => a.payment_gateway)
})

const gatewayNames = computed(() => [...new Set(gatewayAccounts.value.map((a) => a.payment_gateway))])

function toggleGateway(gateway: string, on: boolean) {
	chosenGateways.value = on
		? [...new Set([...chosenGateways.value, gateway])]
		: chosenGateways.value.filter((name) => name !== gateway)
}

async function saveStore() {
	if (!storeName.value.trim()) return
	savingStore.value = true
	try {
		await call('shop.api.onboarding.setup_store', { store_name: storeName.value.trim() })
		step.value = 2
	} catch (error) {
		toast.error('Could not save store details')
	} finally {
		savingStore.value = false
	}
}

async function saveProducts() {
	loadingSamples.value = true
	try {
		if (loadSamples.value) {
			await call('shop.api.onboarding.load_demo_data')
		}
		step.value = 3
	} catch (error) {
		toast.error('Could not load sample products')
	} finally {
		loadingSamples.value = false
	}
}

async function finish() {
	finishing.value = true
	try {
		await call('shop.api.onboarding.update_payments', {
			enable_cod: enableCod.value,
			payment_gateways: chosenGateways.value,
		})
		await call('shop.api.onboarding.complete')
		await fetchOnboardingState(true)
		router.push('/')
	} catch (error) {
		toast.error('Could not complete setup')
	} finally {
		finishing.value = false
	}
}
</script>
