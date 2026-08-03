import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import { defineConfig } from 'vite'

export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: '../shop/www/shop.html',
				outDir: '../shop/public/frontend',
				target: 'es2015',
			},
		}),
		vue(),
	],
	build: {
		target: 'es2015',
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	server: {
		allowedHosts: true,
	},
	optimizeDeps: {
		include: ['frappe-ui > feather-icons', 'engine.io-client', 'socket.io-client'],
		esbuildOptions: {
			plugins: [
				{
					name: 'stub-lucide-icons-in-dep-scan',
					setup(build) {
						build.onResolve({ filter: /^~icons\/lucide\// }, ({ path }) => ({
							path,
							namespace: 'stub-lucide-icon',
						}))
						build.onLoad({ filter: /.*/, namespace: 'stub-lucide-icon' }, () => ({
							contents: 'export default {}',
						}))
					},
				},
			],
		},
	},
})
