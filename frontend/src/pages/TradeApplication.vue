<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div v-if="doc">
			<UiPageHeader
				:title="doc.company_name || doc.contact_name"
				back-to="/trade-accounts?tab=applications"
				back-label="Trade accounts"
			>
				<template #badges>
					<UiStatusBadge :label="doc.state" />
				</template>
				<template v-if="doc.in_desk" #actions>
					<Button :link="`/app/lead/${doc.name}`">Open in Desk</Button>
				</template>
			</UiPageHeader>

			<div class="mt-6 grid gap-6 lg:grid-cols-3">
				<div class="space-y-6 lg:col-span-2">
					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Application</h2>
						<dl class="mt-3 grid gap-x-6 gap-y-3 text-p-sm sm:grid-cols-2">
							<div v-for="field in details" :key="field.label">
								<dt class="text-ink-gray-5">{{ field.label }}</dt>
								<dd class="mt-0.5 break-words text-ink-gray-8">
									<a
										v-if="field.href"
										:href="field.href"
										target="_blank"
										rel="noopener noreferrer"
										class="underline"
									>
										{{ field.value }}
									</a>
									<template v-else>{{ field.value }}</template>
								</dd>
							</div>
						</dl>
					</div>

					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Notes</h2>
						<div v-if="!doc.notes.length" class="mt-2 text-sm text-ink-gray-5">No notes</div>
						<div
							v-for="(note, index) in doc.notes"
							:key="index"
							class="mt-3 border-t border-outline-gray-1 pt-3 first-of-type:border-t-0"
						>
							<p class="whitespace-pre-line text-p-base text-ink-gray-8">{{ note.note }}</p>
							<div class="mt-1 text-sm text-ink-gray-5">
								{{ [note.added_by, formatDateTime(note.added_on)].filter(Boolean).join(' · ') }}
							</div>
						</div>
					</div>
				</div>

				<div class="space-y-6">
					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Decision</h2>
						<template v-if="doc.state === 'Approved'">
							<p class="mt-2 text-p-sm text-ink-gray-7">
								Approved. The applicant signs in to the store as
								<router-link
									:to="`/customers/${encodeURIComponent(doc.customer)}`"
									class="font-medium underline"
								>
									{{ doc.customer }}</router-link
								>, where their trade terms can be changed.
							</p>
						</template>
						<template v-else-if="!doc.trade_enabled">
							<p class="mt-2 text-p-sm text-ink-gray-7">
								Choose the trade customer group in
								<router-link to="/settings" class="underline">Settings</router-link>
								before approving applications.
							</p>
						</template>
						<template v-else>
							<p v-if="doc.state === 'Declined'" class="mt-2 text-p-sm text-ink-gray-7">
								Declined. You can still approve it.
							</p>
							<p class="mt-2 text-p-sm text-ink-gray-5">
								{{
									doc.existing_customer
										? `The applicant's customer ${doc.existing_customer} joins ${doc.customer_group}.`
										: `A new customer in ${doc.customer_group} is made from the application.`
								}}
								They're emailed when it's done, with a link to sign in.
							</p>
							<div class="mt-4 space-y-4">
								<UiPicker
									v-model="form.payment_terms"
									label="Payment terms"
									description="When the customer's invoices are due, e.g. 20th of the following month."
									:options="[{ label: 'None', value: '' }, ...termsOptions]"
								/>
								<Switch
									v-model="form.allow_on_account"
									label="Pay on account at the store"
									class="!w-auto"
								/>
								<FormControl
									v-model.number="form.credit_limit"
									type="number"
									label="Credit limit"
									:min="0"
								/>
							</div>
							<div class="mt-4 flex flex-wrap gap-2">
								<Button variant="solid" :loading="approving" @click="approve">Approve</Button>
								<Button
									v-if="doc.state === 'Waiting'"
									theme="red"
									variant="ghost"
									@click="showDecline = true"
								>
									Decline
								</Button>
							</div>
						</template>
					</div>

					<div class="rounded-lg border border-outline-gray-1 p-4">
						<h2 class="text-base font-medium text-ink-gray-8">Address</h2>
						<div v-if="!doc.addresses.length" class="mt-2 text-sm text-ink-gray-5">No address given</div>
						<div
							v-for="address in doc.addresses"
							:key="address.name"
							class="mt-2 border-t border-outline-gray-1 pt-2 text-p-sm text-ink-gray-6 first:border-t-0 first:pt-0"
							v-html="address.display"
						/>
					</div>
				</div>
			</div>

			<Dialog
				v-model="showDecline"
				:options="{
					title: 'Decline application',
					actions: [
						{ label: 'Decline', variant: 'solid', theme: 'red', loading: declining, onClick: decline },
					],
				}"
			>
				<div class="space-y-3">
					<FormControl v-model="reason" type="textarea" label="Reason" :rows="4" />
					<p class="text-p-sm text-ink-gray-5">
						The applicant is emailed that it was declined, with this reason. They can apply again.
					</p>
				</div>
			</Dialog>
		</div>

		<div v-else-if="application.error" class="flex flex-col items-center gap-3 py-16 text-center">
			<p class="text-p-base text-ink-red-8">{{ errorMessage(application.error, 'Could not load the application') }}</p>
			<Button @click="application.reload()">Try again</Button>
		</div>

		<div v-else class="flex justify-center py-20">
			<Spinner class="size-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, FormControl, Spinner, Switch, call, createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPicker from '@/components/UiPicker.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate, formatDateTime } from '@/utils/format'

const props = defineProps<{ name: string }>()

const router = useRouter()

const application = createResource({
	url: 'shop.api.trade.get_application',
	makeParams: () => ({ lead: props.name }),
	auto: true,
})

const doc = computed(() => application.data)

const form = reactive({ payment_terms: '', allow_on_account: false, credit_limit: 0 })
watch(
	doc,
	(value) => {
		if (!value) return
		Object.assign(form, {
			payment_terms: value.payment_terms || '',
			allow_on_account: false,
			credit_limit: 0,
		})
	},
	{ immediate: true },
)

const termsOptions = computed(() =>
	(doc.value?.payment_terms_templates || []).map((name: string) => ({ label: name, value: name })),
)

const details = computed(() => {
	const value = doc.value
	if (!value) return []
	return [
		{ label: 'Contact', value: value.contact_name },
		{ label: 'Email', value: value.email, href: value.email ? `mailto:${value.email}` : undefined },
		{ label: 'Phone', value: value.phone },
		{ label: 'Website', value: value.website, href: websiteHref(value.website) },
		{ label: 'Country', value: value.country },
		{ label: 'Industry', value: value.industry },
		{ label: 'Tax ID', value: value.tax_id },
		{ label: 'Company number', value: value.company_number },
		{ label: 'Applied', value: formatDate(value.applied_on) },
		{ label: 'Signed in when applying', value: value.signed_in_as || 'No' },
		{ label: 'Terms accepted', value: value.terms_accepted_on ? formatDateTime(value.terms_accepted_on) : '' },
	].filter((field) => field.value)
})

function websiteHref(website?: string) {
	if (!website) return undefined
	return /^https?:\/\//i.test(website) ? website : `https://${website}`
}

function errorMessage(error: unknown, fallback: string) {
	const messages = (error as { messages?: string[] } | null)?.messages
	return messages?.[0] || fallback
}

const approving = ref(false)
async function approve() {
	approving.value = true
	try {
		const result = (await call('shop.api.trade.approve_application', {
			lead: props.name,
			payment_terms: form.payment_terms || null,
			allow_on_account: form.allow_on_account ? 1 : 0,
			credit_limit: form.credit_limit || 0,
		})) as { customer: string }
		toast.success(`Approved: ${result.customer}`)
		router.push(`/customers/${encodeURIComponent(result.customer)}`)
	} catch (error) {
		toast.error(errorMessage(error, 'Could not approve the application'))
	} finally {
		approving.value = false
	}
}

const showDecline = ref(false)
const declining = ref(false)
const reason = ref('')
async function decline() {
	declining.value = true
	try {
		await call('shop.api.trade.decline_application', { lead: props.name, reason: reason.value })
		showDecline.value = false
		reason.value = ''
		toast.success('Application declined')
		application.reload()
	} catch (error) {
		toast.error(errorMessage(error, 'Could not decline the application'))
	} finally {
		declining.value = false
	}
}
</script>
