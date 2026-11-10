declare global {
	interface Window {
		/** Storefront base path from the server, "" or e.g. "/store" (see shop/www/shop.py) */
		shop_route_prefix?: string
	}
}

/** Path of a live storefront page: storefrontPath('product/mug') -> '/store/product/mug' */
export function storefrontPath(path = ''): string {
	const base = window.shop_route_prefix || ''
	const clean = path.replace(/^\/+/, '')
	return clean ? `${base}/${clean}` : base || '/'
}
