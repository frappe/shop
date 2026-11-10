<template>
	<div>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<TabButtons v-model="state" :options="stateTabs" />
			<span class="text-sm text-ink-gray-5">{{ totalLabel }}</span>
		</div>

		<p
			v-if="applications.data && !applications.data.enabled"
			class="mt-4 rounded-lg bg-surface-amber-1 p-3 text-p-sm text-ink-amber-8"
		>
			Choose the trade customer group in
			<router-link to="/settings" class="underline">Settings</router-link>
			before approving applications.
		</p>

		<UiDataTable
			class="mt-4"
			:columns="columns"
			:rows="applications.data?.applications || []"
			row-key="name"
			:loading="!applications.fetched"
			clickable
			@row-click="(row) => router.push(`/trade-accounts/applications/${row.name}`)"
		>
			<template #cell-company_name="{ row }">
				<div class="font-medium text-ink-gray-8">{{ row.company_name || row.lead_name }}</div>
				<div class="text-sm text-ink-gray-5">{{ row.lead_name }}</div>
			</template>
			<template #cell-customer="{ row }">
				<router-link
					v-if="row.customer"
					:to="`/customers/${encodeURIComponent(row.customer)}`"
					class="text-ink-gray-8 hover:underline"
					@click.stop
				>
					{{ row.customer }}
				</router-link>
				<span v-else>-</span>
			</template>
			<template #empty>
				<UiEmptyState :icon="LucideBriefcase" :title="emptyTitle" />
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="PAGE_SIZE" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideBriefcase from '~icons/lucide/briefcase'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPagination from '@/components/UiPagination.vue'
import { formatDate } from '@/utils/format'

const PAGE_SIZE = 20

const router = useRouter()
const state = ref('Waiting')
const start = ref(0)

const stateTabs = ['Waiting', 'Approved', 'Declined'].map((name) => ({ label: name, value: name }))

const applications = createResource({
	url: 'shop.api.trade.get_applications',
	makeParams: () => ({ state: state.value, start: start.value, limit: PAGE_SIZE }),
	auto: true,
	onError: () => toast.error('Could not load trade applications'),
})

watch(state, () => {
	start.value = 0
	applications.reload()
})
watch(start, () => applications.reload())

const total = computed(() => applications.data?.total || 0)
const totalLabel = computed(
	() => `${total.value} ${total.value === 1 ? 'application' : 'applications'}`,
)
const emptyTitle = computed(
	() =>
		({
			Waiting: 'No applications waiting',
			Approved: 'No approved applications',
			Declined: 'No declined applications',
		})[state.value] || 'No applications',
)

const columns = computed(() => [
	{ key: 'company_name', label: 'Business' },
	{ key: 'email_id', label: 'Email' },
	{ key: 'country', label: 'Country' },
	{ key: 'creation', label: 'Applied', format: formatDate },
	...(state.value === 'Approved' ? [{ key: 'customer', label: 'Customer' }] : []),
])
</script>
