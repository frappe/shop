<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<h1 class="text-xl font-semibold text-ink-gray-9">Settings</h1>

		<CatalogListState
			:loading="settings.loading && !settings.data"
			:error="settings.error"
			empty-title=""
			@retry="settings.reload()"
		/>

		<div v-if="settings.data" class="mt-6 space-y-6">
			<CatalogSection title="Store" description="How your store shows up to customers.">
				<FormControl v-model="store.store_name" label="Store name" class="max-w-sm" />
				<CatalogImageInput v-model="store.store_logo" label="Logo" />
				<div class="grid max-w-sm grid-cols-2 gap-4">
					<FormControl :model-value="data.currency" label="Currency" disabled />
					<FormControl :model-value="data.company" label="Company" disabled />
				</div>
				<p class="text-p-sm text-ink-gray-5">
					Currency and company come from your ERPNext setup and cannot be changed here.
				</p>
				<template #footer>
					<Button variant="solid" :loading="saving === 'store'" @click="saveSection('store', store)">
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Payments" description="Choose how customers pay at checkout.">
				<Switch
					v-model="payments.enable_cod"
					label="Cash on Delivery"
					description="Let customers pay in cash when their order arrives."
				/>
				<div class="flex max-w-3xl flex-col gap-3">
					<div class="text-base font-medium text-ink-gray-8">Online payment gateways</div>
					<div
						v-for="(row, index) in payments.payment_gateways"
						:key="index"
						class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
					>
						<FormControl
							v-model="row.payment_gateway"
							type="select"
							label="Payment gateway"
							:options="gatewayOptions"
							class="col-span-3"
						/>
						<FormControl
							v-model="row.label"
							label="Label at checkout"
							placeholder="e.g. Card or PayPal"
							class="col-span-3"
						/>
						<FormControl
							v-model="row.fee_label"
							label="Fee name"
							placeholder="Card fee"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.fee_percent"
							type="number"
							label="Fee %"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.fee_fixed"
							type="number"
							:label="`Fixed fee (${data.company_currency})`"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.fee_percent_international"
							type="number"
							label="Fee % (international)"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.fee_fixed_international"
							type="number"
							:label="`Fixed fee, international (${data.company_currency})`"
							class="col-span-2"
						/>
						<Button
							variant="ghost"
							class="col-span-2 self-end"
							@click="payments.payment_gateways.splice(index, 1)"
						>
							Remove
						</Button>
					</div>
					<div class="flex items-center gap-3">
						<Button :disabled="!gatewayOptions.length" @click="addGateway">Add payment gateway</Button>
						<a
							href="/app/payment-gateway"
							target="_blank"
							class="inline-flex items-center gap-1 text-sm text-ink-gray-6 underline hover:text-ink-gray-8"
						>
							Set up Stripe, PayPal and other gateways in Desk (Payment Gateways)
							<LucideExternalLink class="size-3.5" />
						</a>
					</div>
					<p class="text-p-sm text-ink-gray-5">
						Each gateway is a choice at checkout. An order is charged in the shopper's currency when the
						gateway has a Payment Gateway Account in it, otherwise in the company's currency in ERPNext
						({{ data.company_currency }}). Fixed fees are in that currency. International fees are used
						for orders shipped outside the company's country ({{ data.company_country }}).
					</p>
				</div>
				<UiPicker
					v-model="payments.card_fee_item"
					label="Payment fee item"
					description="A gateway's fee is added to the order as a line with this item."
					:options="feeItemOptions('No payment fee')"
					class="max-w-sm"
				/>
				<NewServiceItem suggestion="Payment fee" @created="(name) => useItem('card_fee_item', name)" />
				<Switch
					v-model="payments.enable_bank_transfer"
					label="Bank transfer"
					description="Customers pay into one of your bank accounts, with the order number as reference."
				/>
				<template v-if="payments.enable_bank_transfer">
					<FormControl
						v-model.number="payments.bank_transfer_days"
						type="number"
						label="Days to pay by bank transfer"
						class="max-w-sm"
					/>
					<div class="flex max-w-3xl flex-col gap-3">
						<div
							v-for="(row, index) in payments.bank_accounts"
							:key="index"
							class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
						>
							<UiPicker
								v-model="row.bank_account"
								label="Bank account"
								description="The ERPNext Bank Account customers pay into by bank transfer."
								:options="bankAccountOptions"
								class="col-span-3"
							/>
							<FormControl
								v-model="row.label"
								label="Label"
								placeholder="e.g. US dollars"
								class="col-span-3"
							/>
							<FormControl
								v-model="row.branch_code_label"
								label="Branch code name"
								placeholder="e.g. BSB, Sort code"
								class="col-span-2"
							/>
							<FormControl
								v-model.number="row.conversion_fee_percent"
								type="number"
								label="Conversion fee %"
								class="col-span-2"
							/>
							<FormControl
								v-model.number="row.local_transfer_fee"
								type="number"
								:label="`Local transfer fee (${bankCurrency(row)})`"
								class="col-span-2"
							/>
							<FormControl
								v-if="bankHasSwift(row)"
								v-model.number="row.swift_transfer_fee"
								type="number"
								:label="`Swift transfer fee (${bankCurrency(row)})`"
								class="col-span-2"
							/>
							<FormControl
								v-model="row.instructions"
								type="textarea"
								label="Instructions"
								class="col-span-5"
							/>
							<Button
								variant="ghost"
								class="col-span-1 self-end"
								@click="payments.bank_accounts.splice(index, 1)"
							>
								Remove
							</Button>
						</div>
						<div>
							<Button @click="addBankAccount">Add bank account</Button>
						</div>
					</div>
					<p class="text-p-sm text-ink-gray-5">
						Transfer fees are what the bank takes from a payment, in the account's currency, and are
						added to the order. Swift transfers are offered when the account's Bank has a SWIFT code.
					</p>
					<div class="grid max-w-lg grid-cols-2 gap-4">
						<UiPicker
							v-model="payments.transfer_fee_item"
							label="Transfer fee item"
							description="The order line a bank's transfer fee is charged on."
							:options="feeItemOptions('No transfer fees')"
						/>
						<UiPicker
							v-model="payments.conversion_fee_item"
							label="Currency conversion item"
							description="The order line a currency conversion fee is charged on."
							:options="feeItemOptions('No conversion fees')"
						/>
						<NewServiceItem suggestion="Bank transfer fee" @created="(name) => useItem('transfer_fee_item', name)" />
						<NewServiceItem
							suggestion="Currency conversion"
							@created="(name) => useItem('conversion_fee_item', name)"
						/>
						<UiPicker
							v-model="payments.bank_charges_account"
							label="Bank charges account"
							description="Where a fee the bank reports taking is booked."
							:options="expenseAccountOptions"
						/>
					</div>
					<a
						href="/app/bank-account"
						target="_blank"
						class="inline-flex items-center gap-1 text-sm text-ink-gray-6 underline hover:text-ink-gray-8"
					>
						Manage bank accounts in Desk
						<LucideExternalLink class="size-3.5" />
					</a>
				</template>
				<template #footer>
					<Button
						variant="solid"
						:loading="saving === 'payments'"
						@click="saveSection('payments', payments)"
					>
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Shipping" description="Delivery charges applied at checkout.">
				<div class="grid max-w-sm grid-cols-2 gap-4">
					<FormControl
						v-model.number="shipping.flat_shipping_rate"
						type="number"
						:label="`Flat rate (${data.currency})`"
						description="0 means shipping is free."
					/>
					<FormControl
						v-model.number="shipping.free_shipping_above"
						type="number"
						:label="`Free shipping above (${data.currency})`"
						description="0 turns this threshold off."
					/>
				</div>
				<UiPicker
					v-model="shipping.shipping_account"
					label="Shipping account"
					description="The income account shipping charges are booked to."
					:options="accountOptions"
					class="max-w-sm"
				/>
				<UiPicker
					v-model="shipping.shipping_item"
					label="Shipping item"
					description="The order line shipping is charged on."
					:options="itemOptions"
					class="max-w-sm"
				/>
				<NewServiceItem suggestion="Shipping" @created="(name) => useItem('shipping_item', name)" />
				<UiPicker
					v-model="shipping.weight_uom"
					label="Weight unit"
					description="The unit product weights are entered in. Carriers price shipping by weight."
					:options="[{ label: 'Kilograms', value: '' }, ...listOptions(data.uoms)]"
					class="max-w-sm"
				/>
				<p class="text-p-sm text-ink-gray-5">
					Shipping is charged as the shipping item's line, or on the shipping account when no item
					is set. One of them is required for shipping charges to apply on orders.
				</p>
				<template #footer>
					<Button
						variant="solid"
						:loading="saving === 'shipping'"
						@click="saveSection('shipping', shipping)"
					>
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection
				title="Duties and import fees"
				description="Countries you send orders to duties paid: checkout charges their duty and your carrier's fees for it as one line."
			>
				<div class="flex max-w-3xl flex-col gap-3">
					<div
						v-for="(row, index) in duties.import_duties"
						:key="index"
						class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
					>
						<UiPicker
							v-model="row.country"
							label="Country"
							description="Orders shipped to this country pay its duties."
							:options="countryOptions"
							class="col-span-3"
						/>
						<FormControl
							v-model.number="row.duty_rate"
							type="number"
							label="Duty %"
							description="Of the goods, before shipping."
							class="col-span-3"
						/>
						<FormControl
							v-model.number="row.fee_on_duty"
							type="number"
							label="Fee on duty %"
							description="What the carrier charges for paying the duty."
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.fee_per_parcel"
							type="number"
							:label="`Fee per parcel (${data.company_currency})`"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.duty_free_up_to"
							type="number"
							:label="`Duty free up to (${data.company_currency})`"
							description="0 means every order pays."
							class="col-span-2"
						/>
						<Button variant="ghost" class="col-span-2 self-end" @click="duties.import_duties.splice(index, 1)">
							Remove
						</Button>
					</div>
					<div>
						<Button @click="addDuty">Add country</Button>
					</div>
				</div>
				<UiPicker
					v-model="duties.duties_item"
					label="Duties item"
					:options="feeItemOptions('No duties item')"
					description="The order line duties are charged on, named as the item is."
					class="max-w-sm"
				/>
				<NewServiceItem suggestion="Duties and Import Fees" @created="(name) => useItem('duties_item', name)" />
				<template #footer>
					<Button variant="solid" :loading="saving === 'duties'" @click="saveSection('duties', duties)">
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection
				title="Shipping surcharges"
				description="Amounts added to each parcel's delivery price when the parcel matches every condition set. With no conditions, a surcharge is added to every delivery. Collection is never charged."
			>
				<div class="flex max-w-3xl flex-col gap-3">
					<div
						v-for="(row, index) in surcharges.shipping_surcharges"
						:key="index"
						class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
					>
						<FormControl
							v-model="row.name"
							label="Name"
							placeholder="e.g. Rural delivery"
							:disabled="row.saved"
							class="col-span-2"
						/>
						<FormControl
							v-model="row.label"
							label="Label at checkout"
							placeholder="Added to the service's name"
							class="col-span-2"
						/>
						<div class="col-span-2 flex items-end">
							<Switch v-model="row.enabled" label="Enabled" class="!w-auto" />
						</div>
						<FormControl
							v-model="row.destination"
							type="select"
							label="Destination"
							:options="destinationOptions"
							class="col-span-2"
						/>
						<Autocomplete
							v-if="listsCountries(row)"
							:model-value="row.countries.map((country) => ({ label: country, value: country }))"
							label="Countries"
							placeholder="Select countries"
							:options="countryOptions"
							multiple
							class="col-span-4"
							@update:model-value="(selected: Option[]) => (row.countries = selected.map((option) => option.value))"
						/>
						<div v-else class="col-span-4" />
						<FormControl
							v-model="row.postcodes"
							type="textarea"
							label="Postcodes"
							placeholder="9016, IV*, 7000...7999"
							description="A postcode, a prefix ending in * or a range of numbers."
							class="col-span-2"
						/>
						<UiPicker
							v-model="row.address_contains"
							label="Address contains"
							description="Only addresses with these words, in any case; # stands for a number. Choose one or type your own."
							:options="addressPatterns"
							empty-label="Any address"
							allow-custom
							class="col-span-2"
						/>
						<UiTagPicker
							:model-value="splitNames(row.services)"
							label="Delivery services"
							description="Only these services: any whose name contains one of them. None chosen means every service."
							:options="data.delivery_services || []"
							placeholder="Every service"
							class="col-span-2"
							@update:model-value="(names: string[]) => (row.services = names.join(', '))"
						/>
						<FormControl
							v-model.number="row.weight_from"
							type="number"
							label="Parcel weight from"
							class="col-span-1"
						/>
						<FormControl v-model.number="row.weight_to" type="number" label="Weight to" class="col-span-1" />
						<FormControl
							v-model.number="row.value_from"
							type="number"
							:label="`Parcel value from (${data.company_currency})`"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.value_to"
							type="number"
							:label="`Value to (${data.company_currency})`"
							description="0 for no limit."
							class="col-span-2"
						/>
						<FormControl
							v-model="row.charge_type"
							type="select"
							label="Charge"
							:options="chargeOptions"
							class="col-span-2"
						/>
						<FormControl
							v-model.number="row.amount"
							type="number"
							:label="row.charge_type === 'Fixed amount' ? `Amount (${data.company_currency})` : 'Percent'"
							class="col-span-2"
						/>
						<div class="col-span-2 flex items-end justify-between gap-2">
							<Switch
								v-if="row.charge_type === 'Fixed amount'"
								v-model="row.amount_includes_tax"
								label="Includes tax"
								class="!w-auto"
							/>
							<span v-else />
							<Button variant="ghost" @click="surcharges.shipping_surcharges.splice(index, 1)">Remove</Button>
						</div>
					</div>
					<div>
						<Button @click="addSurcharge">Add surcharge</Button>
					</div>
				</div>
				<template #footer>
					<Button variant="solid" :loading="saving === 'surcharges'" @click="saveSurcharges">Save</Button>
				</template>
			</CatalogSection>

			<CatalogSection
				title="Shipping restrictions"
				description="Where products can be sent. Pick a restriction here for an Item Group, or on a product to override its group."
			>
				<div class="flex max-w-3xl flex-col gap-3">
					<div
						v-for="(row, index) in restrictions.shipping_restrictions"
						:key="index"
						class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
					>
						<FormControl
							v-model="row.name"
							label="Name"
							placeholder="e.g. Domestic only"
							:disabled="row.saved"
							class="col-span-3"
						/>
						<FormControl
							v-model="row.ships_to"
							type="select"
							label="Ships"
							:options="shipsToOptions"
							class="col-span-3"
						/>
						<Autocomplete
							:model-value="row.countries.map((country) => ({ label: country, value: country }))"
							label="Countries"
							placeholder="Select countries"
							:options="countryOptions"
							multiple
							class="col-span-6"
							@update:model-value="(selected: Option[]) => (row.countries = selected.map((option) => option.value))"
						/>
						<FormControl
							v-model="row.customer_note"
							label="Note on product pages"
							placeholder="Left empty, it lists the countries"
							class="col-span-4"
						/>
						<Button
							variant="ghost"
							class="col-span-2 self-end"
							@click="restrictions.shipping_restrictions.splice(index, 1)"
						>
							Remove
						</Button>
					</div>
					<div>
						<Button @click="addRestriction">Add restriction</Button>
					</div>
				</div>
				<div class="flex max-w-3xl flex-col gap-3">
					<div class="text-base font-medium text-ink-gray-8">Item Groups</div>
					<div
						v-for="(row, index) in restrictions.item_group_restrictions"
						:key="index"
						class="grid grid-cols-6 gap-3"
					>
						<UiPicker
							v-model="row.item_group"
							label="Item Group"
							description="Products in this Item Group, and the groups inside it, follow the restriction."
							:options="listOptions(data.item_groups)"
							class="col-span-3"
						/>
						<FormControl
							v-model="row.restriction"
							type="select"
							label="Restriction"
							:options="restrictionOptions"
							class="col-span-2"
						/>
						<Button
							variant="ghost"
							class="col-span-1 self-end"
							@click="restrictions.item_group_restrictions.splice(index, 1)"
						>
							Remove
						</Button>
					</div>
					<div>
						<Button :disabled="!restrictionOptions.length" @click="addGroupRestriction">
							Add Item Group
						</Button>
					</div>
					<p class="text-p-sm text-ink-gray-5">
						A group's restriction covers the groups under it. Checkout won't send a product where its
						restriction doesn't allow; customers can still collect it from a store location.
					</p>
				</div>
				<template #footer>
					<Button variant="solid" :loading="saving === 'restrictions'" @click="saveRestrictions">
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection
				title="Fulfillment"
				description="The warehouses you sell from and who ships from each, first to last."
			>
				<div class="flex max-w-3xl flex-col gap-3">
					<div
						v-for="(row, index) in fulfillment.fulfillment_locations"
						:key="index"
						class="grid grid-cols-6 gap-3 rounded border border-outline-gray-2 p-3"
					>
						<UiPicker
							v-model="row.warehouse"
							label="Warehouse"
							description="Where stock for these orders is picked from."
							:options="data.warehouses || []"
							class="col-span-3"
						/>
						<FormControl
							v-model="row.display_name"
							label="Name customers see"
							placeholder="e.g. Main store"
							class="col-span-3"
						/>
						<Switch
							v-model="row.show_stock"
							label="Show its stock on product pages"
							class="col-span-3 self-end"
						/>
						<FormControl
							v-model="row.fulfillment_provider"
							type="select"
							label="Shipped by"
							:options="providerOptions"
							class="col-span-3"
						/>
						<UiPicker
							v-model="row.ship_from_address"
							label="Ship from"
							description="The return address on parcels."
							:options="[{ label: 'The warehouse\'s address, else the provider\'s', value: '' }, ...(data.addresses || [])]"
							class="col-span-3"
						/>
						<Switch
							v-model="row.auto_send"
							label="Send paid orders automatically"
							class="col-span-2 self-end"
						/>
						<Switch
							v-model="row.allow_pickup"
							label="Customers can collect here"
							class="col-span-3"
						/>
						<FormControl
							v-if="row.allow_pickup"
							v-model="row.pickup_instructions"
							type="textarea"
							label="Pickup instructions"
							placeholder="Where to go, opening hours, what to bring"
							class="col-span-6"
						/>
						<p v-if="row.warning" class="col-span-6 text-p-sm text-ink-amber-8">{{ row.warning }}</p>
						<div class="col-span-1 flex items-end justify-end gap-1">
							<Button
								variant="ghost"
								:disabled="index === 0"
								:aria-label="'Move up'"
								@click="moveLocation(index, -1)"
							>
								↑
							</Button>
							<Button variant="ghost" @click="fulfillment.fulfillment_locations.splice(index, 1)">
								Remove
							</Button>
						</div>
					</div>
					<div>
						<Button @click="addLocation">Add warehouse</Button>
					</div>
				</div>
				<p class="text-p-sm text-ink-gray-5">
					An order takes each item from the first warehouse that has all of it, and is sent from each
					warehouse as its own parcel. At checkout each parcel is priced by who ships it, and the
					customer picks a service for each.
				</p>
				<p class="text-p-sm text-ink-gray-5">
					Providers marked as needing setup have to be connected before orders can reach them.
				</p>
				<a
					href="/app/shop-amazon-fulfillment-settings"
					target="_blank"
					class="inline-flex items-center gap-1 text-sm text-ink-gray-6 underline hover:text-ink-gray-8"
				>
					Set up Amazon Multi-Channel Fulfillment in Desk
					<LucideExternalLink class="size-3.5" />
				</a>
				<template #footer>
					<Button
						variant="solid"
						:loading="saving === 'fulfillment'"
						@click="saveSection('fulfillment', fulfillment)"
					>
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Catalog" description="Pricing, stock and tax defaults.">
				<div class="grid max-w-lg grid-cols-2 gap-4">
					<UiPicker
						v-model="catalog.price_list"
						label="Price list"
						description="The selling prices the store shows."
						:options="listOptions(data.price_lists)"
					/>
					<FormControl
						v-model.number="catalog.low_stock_threshold"
						type="number"
						label="Low stock threshold"
					/>
					<UiPicker
						v-model="catalog.tax_template"
						label="Tax template"
						description="Taxes added to orders when no Tax Rule matches."
						:options="taxOptions"
					/>
				</div>
				<Switch
					v-model="catalog.allow_out_of_stock"
					label="Allow out of stock orders"
					description="Customers can order items with zero stock."
				/>
				<Switch
					v-model="catalog.prices_include_tax"
					label="Prices include tax"
					description="Storefront prices are treated as tax inclusive."
				/>
				<Switch
					v-model="catalog.show_prices_with_tax"
					label="Show prices with tax"
					description="Show prices with the tax template's tax, and the price without tax under them."
				/>
				<Switch
					v-model="catalog.other_currencies_with_tax"
					label="Show other currencies with tax"
:description="`Off: prices in another currency are shown without tax, as for a buyer outside ${data.company_country || 'the company\'s country'}. Checkout always charges the tax for the delivery address.`"
				/>
				<UiPicker
					v-model="catalog.export_tax_template"
					label="Export tax template"
:description="`Taxes for orders shipped outside ${data.company_country || 'the company\'s country'}, when no Tax Rule for the shopping cart matches.`"
					:options="taxOptions"
					class="max-w-sm"
				/>
				<template #footer>
					<Button
						variant="solid"
						:loading="saving === 'catalog'"
						@click="saveSection('catalog', catalog)"
					>
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Orders" description="What happens to orders after checkout.">
				<UiPicker
					v-model="orders.order_naming_series"
					label="Order naming series"
					description="How web orders are numbered. A short series (e.g. SO-.#####) fits in bank references. New series are added to Sales Order in Document Naming Settings."
					:options="data.order_series || []"
					empty-label="ERPNext's default"
					class="max-w-sm"
				/>
				<Switch
					v-model="orders.round_order_totals"
					label="Round order totals"
					description="ERPNext's Rounded Total: the total is rounded to whole currency units and the customer pays the rounded amount. Off charges the exact amount."
				/>
				<Switch
					v-model="orders.invoice_paid_orders"
					label="Invoice paid orders"
					description="Make the Sales Invoice when an order is paid in full, and email it to the customer."
				/>
				<Switch
					v-model="orders.cancel_unpaid_orders"
					label="Cancel unpaid orders"
					description="Cancel online and bank transfer orders not paid by their due date, and tell the customer."
				/>
				<FormControl
					v-if="orders.cancel_unpaid_orders"
					v-model.number="orders.online_payment_days"
					type="number"
					label="Days to pay online"
					class="max-w-sm"
				/>
				<div class="grid max-w-lg grid-cols-2 gap-4">
					<FormControl
						v-model.number="orders.payment_reminder_hours"
						type="number"
						label="Remind unpaid online orders after (hours)"
						description="0 sends no reminder."
					/>
					<FormControl
						v-model.number="orders.cart_reminder_hours"
						type="number"
						label="Remind left carts after (hours)"
						description="Emails a shopper who left items in their cart, once. 0 sends none; check your country's marketing email rules first."
					/>
					<FormControl
						v-model.number="orders.return_window_days"
						type="number"
						label="Return window (days)"
						description="Days after shipping customers can ask for a return. 0 turns it off."
					/>
					<FormControl
						v-model.number="orders.delivery_days"
						type="number"
						label="Delivery date (days after the order)"
						description="The delivery date store and quote orders get in ERPNext."
					/>
				</div>
				<Switch
					v-model="orders.send_shipping_emails"
					label="Email shipping updates"
					description="Email the customer when their order ships and when it is delivered."
				/>
				<template #footer>
					<Button variant="solid" :loading="saving === 'orders'" @click="saveSection('orders', orders)">
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Accounts" description="Terms, trade accounts and quotes.">
				<Switch
					v-model="accounts.require_terms"
					label="Require terms"
					description="Customers accept your terms when they sign up, order or accept a quote."
				/>
				<div v-if="accounts.require_terms" class="grid max-w-lg grid-cols-2 gap-4">
					<UiPicker
						v-model="accounts.terms_and_conditions"
						label="Terms and conditions"
						description="The terms customers accept, written in Desk."
						:options="listOptions(data.terms_records)"
					/>
					<UiPicker
						v-model="accounts.terms_url"
						label="Terms page"
						description="Where the terms link at checkout goes: a page on the site, or type a full web address."
						:options="data.site_pages || []"
						empty-label="The store's terms page"
						allow-custom
					/>
					<a
						:href="
							accounts.terms_and_conditions
								? `/app/terms-and-conditions/${encodeURIComponent(accounts.terms_and_conditions)}`
								: '/app/terms-and-conditions/new'
						"
						target="_blank"
						class="col-span-2 inline-flex items-center gap-1 text-sm text-ink-gray-6 underline hover:text-ink-gray-8"
					>
						{{ accounts.terms_and_conditions ? 'Edit these terms in Desk' : 'Write your terms in Desk (Terms and Conditions)' }}
						<LucideExternalLink class="size-3.5" />
					</a>
					<FormControl
						v-model="accounts.terms_checkbox_note"
						type="textarea"
						label="Note beside the terms checkbox"
						class="col-span-2"
					/>
					<FormControl
						v-model="accounts.business_buyer_label"
						type="textarea"
						label="Business buyer checkbox"
						description="Shown with the terms; customers buying for a business tick it."
						class="col-span-2"
					/>
				</div>
				<UiPicker
					v-model="accounts.new_customer_group"
					label="Customer Group for new customers"
					description="ERPNext's default Customer Group (Selling Settings): customers who sign up or order online join it, with its prices and pricing rules."
					:options="[{ label: 'Not set', value: '' }, ...listOptions(data.customer_groups)]"
					class="max-w-sm"
				/>
				<UiPicker
					v-model="accounts.trade_customer_group"
					label="Trade Customer Group"
					description="Approved trade customers join this group, with its prices and payment terms."
					:options="[{ label: 'No trade accounts', value: '' }, ...listOptions(data.customer_groups)]"
					class="max-w-sm"
				/>
				<Switch
					v-if="accounts.trade_customer_group"
					v-model="accounts.email_statements"
					label="Email monthly statements"
					description="Each trade customer gets a statement every month."
				/>
				<Switch
					v-if="accounts.trade_customer_group"
					v-model="accounts.allow_trade_applications"
					label="Trade applications"
					description="Businesses can apply for a trade account from the storefront."
				/>
				<p v-if="data.trade_customer_group" class="text-p-sm text-ink-gray-5">
					Trade rates, accounts and applications are in
					<router-link to="/trade-accounts" class="underline">Trade accounts</router-link>.
				</p>
				<Switch
					v-model="accounts.allow_quote_requests"
					label="Quote requests"
					description="Shoppers can ask for a quote at checkout instead of ordering."
				/>
				<FormControl
					v-if="accounts.allow_quote_requests"
					v-model.number="accounts.quote_valid_days"
					type="number"
					label="Quotes valid for (days)"
					class="max-w-sm"
				/>
				<FormControl
					v-model="accounts.staff_notification_emails"
					type="textarea"
					label="Staff notification emails"
					description="Who is told of trade applications, quote requests and returns, one per line. Empty tells every Shop Manager and Sales Manager."
					class="max-w-lg"
				/>
				<template #footer>
					<Button variant="solid" :loading="saving === 'accounts'" @click="saveSection('accounts', accounts)">
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection title="Storefront" description="Your storefront pages are built with Builder.">
				<template #header-action>
					<Button @click="openBuilder">
						<template #prefix><LucideExternalLink class="size-3.5" /></template>
						Edit in Builder
					</Button>
				</template>
				<StorefrontThemes @applied="settings.reload()" />
				<FormControl
					v-model="storefront.route_prefix"
					label="Route prefix"
					placeholder="e.g. store"
					description="Serve the storefront under a path of the site, such as /store. Empty serves it at the site's root."
					class="max-w-sm"
				/>
				<FormControl
					v-model="storefront.menu_label"
					label="Catalogue menu label"
					placeholder="Products"
					description="The menu in the store's header that lists your collections. Empty shows Products."
					class="max-w-sm"
				/>
				<Switch
					v-model="storefront.customers_land_in_store"
					label="Customers land in the store"
					description="After signing in or setting a password, customers go to their store account, not the site's home page. Frappe's /me page sends them there too."
					class="!w-auto"
				/>
				<template #footer>
					<Button
						variant="solid"
						:loading="saving === 'storefront'"
						@click="saveSection('storefront', storefront)"
					>
						Save
					</Button>
				</template>
			</CatalogSection>

			<CatalogSection
				title="Address lookup"
				description="Suggests addresses as customers type one at checkout, in their account and on trade applications."
			>
				<template v-if="data.address_lookup?.installed" #header-action>
					<Button @click="openLookupSettings">
						<template #prefix><LucideExternalLink class="size-3.5" /></template>
						Set up in Desk
					</Button>
				</template>
				<p class="max-w-2xl text-p-sm text-ink-gray-6">
					<template v-if="!data.address_lookup?.installed">
						No app on this site looks addresses up. ERPNext Shipping does, with Photon (OpenStreetMap, free) or
						Google Places.
					</template>
					<template v-else-if="data.address_lookup.enabled">
						{{ data.address_lookup.service }} suggests addresses here and in Desk's Address forms. The service is
						chosen in Address Lookup Settings.
					</template>
					<template v-else>
						Off. Choose Photon (OpenStreetMap, free) or Google Places in Address Lookup Settings, and addresses are
						suggested here and in Desk's Address forms.
					</template>
				</p>
				<UiPicker
					v-if="data.address_lookup?.enabled"
					v-model="lookupTry"
					label="Try it"
					description="Type the start of an address to see what customers will be offered."
					:search="tryLookup"
					placeholder="e.g. 12 Queen Street"
					class="max-w-sm"
				/>
			</CatalogSection>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Autocomplete, FormControl, Switch, call, createResource, toast } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'

import CatalogImageInput from '@/components/CatalogImageInput.vue'
import CatalogListState from '@/components/CatalogListState.vue'
import CatalogSection from '@/components/CatalogSection.vue'
import NewServiceItem from '@/components/NewServiceItem.vue'
import StorefrontThemes from '@/components/StorefrontThemes.vue'
import UiPicker from '@/components/UiPicker.vue'
import UiTagPicker from '@/components/UiTagPicker.vue'

const saving = ref('')

const store = reactive({ store_name: '', store_logo: '' })
const payments = reactive({
	enable_cod: true,
	payment_gateways: [] as GatewayRow[],
	card_fee_item: '',
	enable_bank_transfer: false,
	bank_transfer_days: 7,
	bank_accounts: [] as BankAccountRow[],
	transfer_fee_item: '',
	conversion_fee_item: '',
	bank_charges_account: '',
})
const shipping = reactive({
	flat_shipping_rate: 0,
	free_shipping_above: 0,
	shipping_account: '',
	shipping_item: '',
	weight_uom: '',
})
const duties = reactive({ duties_item: '', import_duties: [] as DutyRow[] })
const surcharges = reactive({ shipping_surcharges: [] as SurchargeRow[] })
const restrictions = reactive({
	shipping_restrictions: [] as RestrictionRow[],
	item_group_restrictions: [] as GroupRestrictionRow[],
})
const orders = reactive({
	round_order_totals: true,
	invoice_paid_orders: false,
	cancel_unpaid_orders: false,
	online_payment_days: 2,
	order_naming_series: '',
	payment_reminder_hours: 1,
	cart_reminder_hours: 0,
	return_window_days: 14,
	delivery_days: 3,
	send_shipping_emails: false,
})
const accounts = reactive({
	new_customer_group: '',
	require_terms: false,
	terms_and_conditions: '',
	terms_url: '',
	trade_customer_group: '',
	email_statements: false,
	allow_quote_requests: false,
	quote_valid_days: 30,
	business_buyer_label: '',
	terms_checkbox_note: '',
	allow_trade_applications: true,
	staff_notification_emails: '',
})
const storefront = reactive({ route_prefix: '', menu_label: '', customers_land_in_store: true })
const lookupTry = ref('')
type Option = { label: string; value: string }

type RestrictionRow = {
	name: string
	ships_to: string
	countries: string[]
	customer_note: string
	saved?: boolean
}

type GroupRestrictionRow = { item_group: string; restriction: string }

const shipsToOptions = [
	{ label: 'Only to these countries', value: 'Only to these countries' },
	{ label: 'Everywhere except these countries', value: 'Everywhere except these countries' },
]

const restrictionOptions = computed(() =>
	restrictions.shipping_restrictions
		.filter((row) => row.saved)
		.map((row) => ({ label: row.name, value: row.name })),
)

function addRestriction() {
	restrictions.shipping_restrictions.push({
		name: '',
		ships_to: 'Only to these countries',
		countries: data.value.company_country ? [data.value.company_country] : [],
		customer_note: '',
	})
}

function addGroupRestriction() {
	const used = restrictions.item_group_restrictions.map((row) => row.item_group)
	const next = (data.value.item_groups || []).find((group: string) => !used.includes(group))
	restrictions.item_group_restrictions.push({
		item_group: next || '',
		restriction: restrictionOptions.value[0]?.value || '',
	})
}

async function saveRestrictions() {
	saving.value = 'restrictions'
	try {
		const saved = await call('shop.api.settings.save_shipping_restrictions', {
			restrictions: restrictions.shipping_restrictions,
			item_groups: restrictions.item_group_restrictions,
		})
		savedSection.value = 'restrictions'
		settings.data = { ...settings.data, ...saved }
		toast.success('Settings saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save settings')
	} finally {
		saving.value = ''
	}
}

type SurchargeRow = {
	name: string
	label: string
	enabled: boolean
	destination: string
	countries: string[]
	postcodes: string
	address_contains: string
	services: string
	weight_from: number
	weight_to: number
	value_from: number
	value_to: number
	charge_type: string
	amount: number
	amount_includes_tax: boolean
	saved?: boolean
}

const destinationOptions = [
	'Everywhere',
	"Within the store's country",
	'Abroad',
	'Only these countries',
	'Everywhere except these countries',
].map((value) => ({ label: value, value }))

const chargeOptions = ['Fixed amount', 'Percent of the delivery price'].map((value) => ({ label: value, value }))

function listsCountries(row: SurchargeRow) {
	return row.destination === 'Only these countries' || row.destination === 'Everywhere except these countries'
}

function addSurcharge() {
	surcharges.shipping_surcharges.push({
		name: '',
		label: '',
		enabled: true,
		destination: 'Everywhere',
		countries: [],
		postcodes: '',
		address_contains: '',
		services: '',
		weight_from: 0,
		weight_to: 0,
		value_from: 0,
		value_to: 0,
		charge_type: 'Fixed amount',
		amount: 0,
		amount_includes_tax: true,
	})
}

async function saveSurcharges() {
	saving.value = 'surcharges'
	try {
		const saved = await call('shop.api.settings.save_shipping_surcharges', {
			surcharges: surcharges.shipping_surcharges,
		})
		savedSection.value = 'surcharges'
		settings.data = { ...settings.data, shipping_surcharges: saved }
		toast.success('Settings saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save settings')
	} finally {
		saving.value = ''
	}
}

type DutyRow = {
	country: string
	duty_rate: number
	fee_on_duty: number
	fee_per_parcel: number
	duty_free_up_to: number
}

const countryOptions = computed(() => listOptions(data.value.countries))

function addDuty() {
	const used = duties.import_duties.map((row) => row.country)
	const next = (data.value.countries || []).find(
		(country: string) => country !== data.value.company_country && !used.includes(country),
	)
	duties.import_duties.push({
		country: next || '',
		duty_rate: 0,
		fee_on_duty: 0,
		fee_per_parcel: 0,
		duty_free_up_to: 0,
	})
}

type LocationRow = {
	warehouse: string
	display_name: string
	show_stock: boolean
	allow_pickup: boolean
	pickup_instructions: string
	fulfillment_provider: string
	ship_from_address: string
	auto_send: boolean
	warning?: string | null
}

const fulfillment = reactive({ fulfillment_locations: [] as LocationRow[] })

function addLocation() {
	const used = fulfillment.fulfillment_locations.map((row) => row.warehouse)
	const next = (data.value.warehouses || []).find((option: { value: string }) => !used.includes(option.value))
	fulfillment.fulfillment_locations.push({
		warehouse: next?.value || '',
		display_name: '',
		show_stock: false,
		allow_pickup: false,
		pickup_instructions: '',
		fulfillment_provider: 'manual',
		ship_from_address: '',
		auto_send: false,
	})
}

function moveLocation(index: number, step: number) {
	const rows = fulfillment.fulfillment_locations
	const [row] = rows.splice(index, 1)
	rows.splice(index + step, 0, row)
}
const catalog = reactive({
	price_list: '',
	low_stock_threshold: 0,
	tax_template: '',
	export_tax_template: '',
	allow_out_of_stock: false,
	prices_include_tax: false,
	show_prices_with_tax: false,
	other_currencies_with_tax: false,
})

const settings = createResource({
	url: 'shop.api.settings.get_settings',
	auto: true,
})

const data = computed(() => settings.data || {})

const savedSection = ref('')

watch(
	() => settings.data,
	(doc) => {
		if (doc) hydrate(doc, savedSection.value)
		savedSection.value = ''
	},
	{ immediate: true },
)

// a section's form is filled from the saved settings; saving one section leaves the others' edits
function hydrate(doc: Record<string, any>, only = '') {
	const fill = (section: string) => !only || only === section
	if (fill('store')) Object.assign(store, { store_name: doc.store_name || '', store_logo: doc.store_logo || '' })
	if (fill('payments')) Object.assign(payments, {
		enable_cod: !!doc.enable_cod,
		payment_gateways: (doc.payment_gateways || []).map((row: GatewayRow) => ({ ...row })),
		card_fee_item: doc.card_fee_item || '',
		enable_bank_transfer: !!doc.enable_bank_transfer,
		bank_transfer_days: doc.bank_transfer_days || 7,
		bank_accounts: (doc.bank_accounts || []).map((row: BankAccountRow) => ({ ...row })),
		transfer_fee_item: doc.transfer_fee_item || '',
		conversion_fee_item: doc.conversion_fee_item || '',
		bank_charges_account: doc.bank_charges_account || '',
	})
	if (fill('shipping')) Object.assign(shipping, {
		flat_shipping_rate: doc.flat_shipping_rate || 0,
		free_shipping_above: doc.free_shipping_above || 0,
		shipping_account: doc.shipping_account || '',
		shipping_item: doc.shipping_item || '',
		weight_uom: doc.weight_uom || '',
	})
	if (fill('surcharges')) Object.assign(surcharges, {
		shipping_surcharges: (doc.shipping_surcharges || []).map((row: SurchargeRow) => ({
			...row,
			enabled: !!row.enabled,
			amount_includes_tax: !!row.amount_includes_tax,
			postcodes: row.postcodes || '',
			address_contains: row.address_contains || '',
			services: row.services || '',
			countries: [...(row.countries || [])],
			saved: true,
		})),
	})
	if (fill('restrictions')) Object.assign(restrictions, {
		shipping_restrictions: (doc.shipping_restrictions || []).map((row: RestrictionRow) => ({
			...row,
			countries: [...(row.countries || [])],
			saved: true,
		})),
		item_group_restrictions: (doc.item_group_restrictions || []).map((row: GroupRestrictionRow) => ({ ...row })),
	})
	if (fill('duties')) Object.assign(duties, {
		duties_item: doc.duties_item || '',
		import_duties: (doc.import_duties || []).map((row: DutyRow) => ({ ...row })),
	})
	if (fill('orders')) Object.assign(orders, {
		invoice_paid_orders: !!doc.invoice_paid_orders,
		cancel_unpaid_orders: !!doc.cancel_unpaid_orders,
		online_payment_days: doc.online_payment_days || 2,
		order_naming_series: doc.order_naming_series || '',
		round_order_totals: !!doc.round_order_totals,
		payment_reminder_hours: doc.payment_reminder_hours ?? 1,
		cart_reminder_hours: doc.cart_reminder_hours ?? 0,
		return_window_days: doc.return_window_days ?? 14,
		delivery_days: doc.delivery_days ?? 3,
		send_shipping_emails: !!doc.send_shipping_emails,
	})
	if (fill('accounts')) Object.assign(accounts, {
		require_terms: !!doc.require_terms,
		terms_and_conditions: doc.terms_and_conditions || '',
		terms_url: doc.terms_url || '',
		trade_customer_group: doc.trade_customer_group || '',
		new_customer_group: doc.new_customer_group || '',
		email_statements: !!doc.email_statements,
		allow_quote_requests: !!doc.allow_quote_requests,
		quote_valid_days: doc.quote_valid_days || 30,
		business_buyer_label: doc.business_buyer_label || '',
		terms_checkbox_note: doc.terms_checkbox_note || '',
		allow_trade_applications: !!doc.allow_trade_applications,
		staff_notification_emails: doc.staff_notification_emails || '',
	})
	if (fill('fulfillment')) Object.assign(fulfillment, {
		fulfillment_locations: (doc.fulfillment_locations || []).map((row: LocationRow) => ({
			...row,
			ship_from_address: row.ship_from_address || '',
			display_name: row.display_name || '',
			show_stock: !!row.show_stock,
			allow_pickup: !!row.allow_pickup,
			pickup_instructions: row.pickup_instructions || '',
			auto_send: !!row.auto_send,
		})),
	})

	if (fill('catalog')) Object.assign(catalog, {
		price_list: doc.price_list || '',
		low_stock_threshold: doc.low_stock_threshold || 0,
		tax_template: doc.tax_template || '',
		export_tax_template: doc.export_tax_template || '',
		allow_out_of_stock: !!doc.allow_out_of_stock,
		prices_include_tax: !!doc.prices_include_tax,
		show_prices_with_tax: !!doc.show_prices_with_tax,
		other_currencies_with_tax: !!doc.other_currencies_with_tax,
	})
	if (fill('storefront'))
		Object.assign(storefront, {
			route_prefix: doc.route_prefix || '',
			menu_label: doc.menu_label || '',
			customers_land_in_store: !!doc.customers_land_in_store,
		})
}

type GatewayRow = {
	payment_gateway: string
	label: string
	fee_label: string
	fee_percent: number
	fee_fixed: number
	fee_percent_international: number
	fee_fixed_international: number
}

const gatewayOptions = computed(() => {
	const currencies: Record<string, string[]> = {}
	for (const a of (data.value.gateway_accounts || []) as { payment_gateway: string; currency: string }[]) {
		;(currencies[a.payment_gateway] ||= []).push(a.currency)
	}
	return Object.entries(currencies).map(([gateway, list]) => ({
		label: `${gateway} (${list.join(', ')})`,
		value: gateway,
	}))
})

function addGateway() {
	const used = payments.payment_gateways.map((row) => row.payment_gateway)
	const next = gatewayOptions.value.find((option) => !used.includes(option.value))
	payments.payment_gateways.push({
		payment_gateway: next?.value || '',
		label: '',
		fee_label: '',
		fee_percent: 0,
		fee_fixed: 0,
		fee_percent_international: 0,
		fee_fixed_international: 0,
	})
}

const accountOptions = computed(() => [
	{ label: 'No shipping account', value: '' },
	...listOptions(data.value.income_accounts),
])

const providerOptions = computed(() =>
	(data.value.fulfillment_providers || []).map(
		(provider: { key: string; label: string; configured: boolean }) => ({
			label: provider.configured ? provider.label : `${provider.label} (needs setup)`,
			value: provider.key,
		}),
	),
)

type BankAccountRow = {
	bank_account: string
	label: string
	branch_code_label: string
	conversion_fee_percent: number
	local_transfer_fee: number
	swift_transfer_fee: number
	instructions: string
}

type CompanyBankAccount = { name: string; currency: string | null; swift: boolean }

const bankAccountOptions = computed(() =>
	(data.value.company_bank_accounts || []).map((account: CompanyBankAccount) => ({
		label: account.currency ? `${account.name} (${account.currency})` : account.name,
		value: account.name,
	})),
)

function companyBankAccount(row: BankAccountRow): CompanyBankAccount | undefined {
	return (data.value.company_bank_accounts || []).find(
		(account: CompanyBankAccount) => account.name === row.bank_account,
	)
}

function bankCurrency(row: BankAccountRow) {
	return companyBankAccount(row)?.currency || data.value.currency
}

function bankHasSwift(row: BankAccountRow) {
	return !!companyBankAccount(row)?.swift
}

function addBankAccount() {
	payments.bank_accounts.push({
		bank_account: '',
		label: '',
		branch_code_label: '',
		conversion_fee_percent: 0,
		local_transfer_fee: 0,
		swift_transfer_fee: 0,
		instructions: '',
	})
}

function feeItemOptions(none: string) {
	return [{ label: none, value: '' }, ...listOptions(data.value.service_items)]
}

const expenseAccountOptions = computed(() => [
	{ label: 'Not set', value: '' },
	...listOptions(data.value.expense_accounts),
])

const itemOptions = computed(() => [
	{ label: 'No shipping item', value: '' },
	...listOptions(data.value.service_items),
])

const taxOptions = computed(() => [
	{ label: 'No tax template', value: '' },
	...listOptions(data.value.tax_templates),
])

// a new service item joins the choices and is picked; the section is saved as usual
function useItem(
	field: 'card_fee_item' | 'transfer_fee_item' | 'conversion_fee_item' | 'shipping_item' | 'duties_item',
	name: string,
) {
	settings.data.service_items = [...(settings.data.service_items || []), { label: name, value: name }]
	if (field === 'shipping_item') shipping.shipping_item = name
	else if (field === 'duties_item') duties.duties_item = name
	else payments[field] = name
	toast.success(`${name} created. Save to use it.`)
}

const addressPatterns = [
	{ label: 'PO Box', value: 'PO Box' },
	{ label: 'Private Bag', value: 'Private Bag' },
	{ label: 'RD # (rural delivery)', value: 'RD #' },
]

function splitNames(text?: string) {
	return (text || '')
		.split(',')
		.map((name) => name.trim())
		.filter(Boolean)
}

function listOptions(names?: (string | { label: string; value: string })[]) {
	return (names || []).map((name) => (typeof name === 'string' ? { label: name, value: name } : name))
}

async function saveSection(section: string, payload: Record<string, any>) {
	saving.value = section
	try {
		const saved = await call('shop.api.settings.save_settings', {
			payload: normalize(payload),
		})
		savedSection.value = section
		settings.data = saved
		toast.success('Settings saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save settings')
	} finally {
		saving.value = ''
	}
}

function openLookupSettings() {
	window.open(data.value.address_lookup.settings_url, '_blank')
}

async function tryLookup(text: string) {
	if (text.trim().length < 3) return []
	const result = await call('shop.storefront.address_lookup.suggest', { text, country: data.value.company_country })
	return (result.suggestions || []).map((row: { id: string; label: string; detail: string }) => ({
		label: row.label,
		value: row.id,
		description: row.detail,
	}))
}

function normalize(payload: Record<string, any>) {
	// Empty select values mean "unset" for link fields.
	return Object.fromEntries(
		Object.entries(payload).map(([key, value]) => [key, value === '' ? null : value]),
	)
}

function openBuilder() {
	window.open('/builder', '_blank')
}
</script>
