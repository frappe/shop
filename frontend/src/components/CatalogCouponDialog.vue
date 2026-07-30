<template>
	<Dialog
		v-model="show"
		:options="{
			title: editRow ? 'Edit coupon' : 'New coupon',
			actions: [{ label: editRow ? 'Save' : 'Create', variant: 'solid', onClick: save }],
		}"
	>
		<div class="space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					v-model="form.coupon_code"
					label="Code"
					placeholder="SUMMER20"
					required
					description="Codes are saved in uppercase"
				/>
				<FormControl v-model="form.coupon_name" label="Name" placeholder="Summer sale" />
			</div>
			<div class="grid grid-cols-2 gap-4">
				<FormControl v-model="form.discount_type" type="select" label="Type" :options="typeOptions" />
				<FormControl
					v-model.number="form.value"
					type="number"
					:label="form.discount_type === 'Percentage' ? 'Percent off' : 'Amount off'"
					required
				/>
			</div>
			<FormControl
				v-model.number="form.min_amt"
				type="number"
				label="Minimum spend"
				description="Order total needed before the coupon applies"
				class="w-48"
			/>
			<div class="grid grid-cols-2 gap-4">
				<FormControl v-model="form.valid_from" type="date" label="Valid from" />
				<FormControl v-model="form.valid_upto" type="date" label="Valid until" />
			</div>
			<FormControl
				v-model.number="form.maximum_use"
				type="number"
				label="Maximum uses"
				description="0 means unlimited"
				class="w-48"
			/>
			<Switch v-model="form.enabled" label="Enabled" class="!w-auto" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { Dialog, FormControl, Switch, call, toast } from 'frappe-ui'

export interface CouponRow {
	name: string
	coupon_name: string
	coupon_code: string
	used: number
	maximum_use: number
	valid_from: string | null
	valid_upto: string | null
	discount_type: string
	discount_percentage: number
	discount_amount: number
	min_amt: number
	enabled: boolean
	value_label: string
}

const props = defineProps<{ editRow: CouponRow | null }>()

const show = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const typeOptions = [
	{ label: 'Percentage', value: 'Percentage' },
	{ label: 'Amount', value: 'Amount' },
]

const form = reactive({
	coupon_code: '',
	coupon_name: '',
	discount_type: 'Percentage',
	value: 0,
	min_amt: 0,
	valid_from: '',
	valid_upto: '',
	maximum_use: 0,
	enabled: true,
})

watch(show, (open) => {
	if (open) reset()
})

function reset() {
	const row = props.editRow
	Object.assign(form, {
		coupon_code: row?.coupon_code || '',
		coupon_name: row?.coupon_name || '',
		discount_type: row?.discount_type || 'Percentage',
		value: row?.value || 0,
		min_amt: row?.min_amt || 0,
		valid_from: row?.valid_from || '',
		valid_upto: row?.valid_upto || '',
		maximum_use: row?.maximum_use || 0,
		enabled: row ? !!row.enabled : true,
	})
}

async function save() {
	if (!form.coupon_code.trim()) {
		toast.error('Coupon code is required')
		return
	}
	if (!form.value || form.value <= 0) {
		toast.error('Discount value must be greater than zero')
		return
	}
	try {
		await call('shop.api.discounts.save_coupon', {
			payload: { name: props.editRow?.name, ...form },
		})
		toast.success(props.editRow ? 'Coupon saved' : 'Coupon created')
		show.value = false
		emit('saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save coupon')
	}
}
</script>
