<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader
			title="Trade accounts"
			subtitle="Businesses that buy at trade prices: their accounts, applications and rates."
		/>

		<TabButtons v-model="tab" class="mt-6" :options="tabs" />

		<div class="mt-4">
			<template v-if="tab === 'accounts'">
				<p
					v-if="accounts.data && !accounts.data.enabled"
					class="rounded-lg bg-surface-amber-1 p-3 text-p-sm text-ink-amber-8"
				>
					Choose the trade customer group in
					<router-link to="/settings" class="underline">Settings</router-link>
					to have trade accounts.
				</p>
				<template v-else>
					<UiFilterBar v-model="search" search-placeholder="Search trade accounts">
						<template #trailing>{{ totalLabel }}</template>
					</UiFilterBar>
					<UiDataTable
						class="mt-4"
						:columns="columns"
						:rows="accounts.data?.accounts || []"
						row-key="name"
						:loading="!accounts.fetched"
						clickable
						@row-click="(row) => router.push(`/customers/${encodeURIComponent(row.name)}`)"
					>
						<template #cell-customer_name="{ row }">
							<span class="font-medium text-ink-gray-8">{{ row.customer_name }}</span>
						</template>
						<template #cell-allow_on_account="{ row }">{{ row.allow_on_account ? 'Yes' : 'No' }}</template>
						<template #cell-own_rates="{ row }">{{ row.own_rates || '-' }}</template>
						<template #empty>
							<UiEmptyState
								:icon="LucideBriefcase"
								title="No trade accounts yet"
								message="Approve an application, or make a customer a trade customer on their page."
							/>
						</template>
					</UiDataTable>
					<UiPagination v-model:start="start" class="mt-4" :limit="PAGE_SIZE" :total="total" />
				</template>
			</template>

			<TradeApplicationList v-else-if="tab === 'applications'" />

			<div v-else class="rounded-lg border border-outline-gray-1 p-4">
				<PricingRates
					scope="trade"
					title="Trade rates"
					description="What every trade account gets: percent off or a set price for an Item Group or a product, with quantity breaks. A customer's own rates are on their page."
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, createResource, toast } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'

import LucideBriefcase from '~icons/lucide/briefcase'

import PricingRates from '@/components/PricingRates.vue'
import TradeApplicationList from '@/components/TradeApplicationList.vue'
import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiFilterBar from '@/components/UiFilterBar.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'

const PAGE_SIZE = 20
const TABS = ['accounts', 'applications', 'rates']

const route = useRoute()
const router = useRouter()

const tabs = [
	{ label: 'Accounts', value: 'accounts' },
	{ label: 'Applications', value: 'applications' },
	{ label: 'Trade rates', value: 'rates' },
]
const tab = ref(TABS.includes(String(route.query.tab)) ? String(route.query.tab) : 'accounts')
watch(tab, (value) => router.replace({ query: { ...route.query, tab: value } }))

const search = ref('')
const start = ref(0)
const accounts = createResource({
	url: 'shop.api.trade.get_trade_accounts',
	makeParams: () => ({ search: search.value || undefined, start: start.value, limit: PAGE_SIZE }),
	auto: true,
	onError: () => toast.error('Could not load trade accounts'),
})
watch(search, () => {
	start.value = 0
	accounts.reload()
})
watch(start, () => accounts.reload())

const total = computed(() => accounts.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'account' : 'accounts'}`)

const columns = [
	{ key: 'customer_name', label: 'Customer' },
	{ key: 'payment_terms', label: 'Payment terms' },
	{ key: 'allow_on_account', label: 'On account' },
	{ key: 'formatted_credit_limit', label: 'Credit limit', align: 'right' as const },
	{ key: 'formatted_outstanding', label: 'Owing', align: 'right' as const },
	{ key: 'own_rates', label: 'Own rates', align: 'right' as const },
]
</script>
