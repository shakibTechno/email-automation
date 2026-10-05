import { useEffect, useRef, useCallback, useImperativeHandle, forwardRef, useState } from 'react';
import grapesjs, { Editor } from 'grapesjs';
import 'grapesjs/dist/css/grapes.min.css';
import 'grapesjs-preset-webpage';
import { LayoutGrid, Layers, Palette, SlidersHorizontal, ChevronLeft, ChevronRight, ClipboardList, Plus, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface GrapesJSEditorRef {
  save: () => void;
  setDevice: (device: 'Desktop' | 'Tablet' | 'Mobile') => void;
}

export interface EmbeddableForm {
  id: string;
  name: string;
  form_type: string;
}

interface GrapesJSEditorProps {
  initialHtml?: string;
  initialCss?: string;
  initialData?: Record<string, any>;
  onSave: (data: {
    html: string;
    css: string;
    designJson: Record<string, any>;
  }) => void;
  onLoad?: () => void;
  forms?: EmbeddableForm[];
}

export const GrapesJSEditor = forwardRef<GrapesJSEditorRef, GrapesJSEditorProps>(
  ({ initialHtml = '', initialCss = '', initialData, onSave, onLoad, forms = [] }, ref) => {
    const editorRef = useRef<Editor | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleSave = useCallback(() => {
      if (!editorRef.current) return;
      const editor = editorRef.current;

      const html = editor.getHtml() || '';
      const css = editor.getCss() || '';
      const designJson = editor.getProjectData();

      onSave({ html, css, designJson });
    }, [onSave]);

    // Expose save + setDevice to parent via ref
    useImperativeHandle(ref, () => ({
      save: handleSave,
      setDevice: (device: 'Desktop' | 'Tablet' | 'Mobile') => {
        editorRef.current?.Devices.select(device);
      },
    }), [handleSave]);

    // Panel tab state
    const [leftTab, setLeftTab] = useState<'blocks' | 'layers' | 'forms'>('blocks');
    const [rightTab, setRightTab] = useState<'style' | 'properties'>('style');
    const [leftCollapsed, setLeftCollapsed] = useState(false);

    // Insert a form as an iframe block into the canvas
    const handleInsertForm = (form: EmbeddableForm) => {
      if (!editorRef.current) return;
      const formTypeLabel = form.form_type.replace(/_/g, ' ');
      // Use absolute URL so the iframe resolves correctly when the page is
      // served by Django (which has no /f/ route — only the React SPA does).
      const formUrl = `${window.location.origin}/f/${form.id}`;
      editorRef.current.addComponents(`
        <div class="ea-form-embed" data-form-id="${form.id}" style="width:100%;max-width:640px;margin:0 auto;padding:16px 0;">
          <div style="margin-bottom:8px;display:flex;align-items:center;gap:6px;">
            <span style="font-size:12px;font-weight:600;color:#374151;">${form.name}</span>
            <span style="font-size:10px;background:#f3f4f6;color:#6b7280;padding:2px 8px;border-radius:99px;text-transform:capitalize;">${formTypeLabel}</span>
          </div>
          <iframe
            src="${formUrl}"
            width="100%"
            height="520"
            frameborder="0"
            style="width:100%;height:520px;border:none;border-radius:8px;display:block;"
            title="${form.name}"
            loading="lazy"
          ></iframe>
        </div>
      `);
    };

    useEffect(() => {
      if (!containerRef.current || editorRef.current) return;

      const editor = grapesjs.init({
        container: containerRef.current,
        height: '100%',
        width: 'auto',
        storageManager: false,
        plugins: ['grapesjs-preset-webpage'],
        pluginsOpts: {
          'grapesjs-preset-webpage': {
            blocksBasicOpts: {
              flexGrid: true,
            },
            navbarOpts: false,
            countdownOpts: false,
            formsOpts: false,
          },
        },
        canvas: {
          styles: [
            'https://cdn.tailwindcss.com',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
          ],
          scripts: [
            'https://cdn.tailwindcss.com',
          ],
        },
        deviceManager: {
          devices: [
            { name: 'Desktop', width: '' },
            { name: 'Tablet', width: '768px', widthMedia: '768px' },
            { name: 'Mobile', width: '375px', widthMedia: '375px' },
          ],
        },
        blockManager: {
          appendTo: '#blocks-container',
        },
        layerManager: {
          appendTo: '#layers-container',
        },
        styleManager: {
          appendTo: '#styles-container',
          sectors: [
            {
              name: 'General',
              open: false,
              buildProps: ['float', 'display', 'position', 'top', 'right', 'left', 'bottom'],
            },
            {
              name: 'Flex',
              open: false,
              buildProps: ['flex-direction', 'flex-wrap', 'justify-content', 'align-items', 'align-content', 'order', 'flex-basis', 'flex-grow', 'flex-shrink', 'align-self'],
            },
            {
              name: 'Dimension',
              open: false,
              buildProps: ['width', 'height', 'max-width', 'min-width', 'min-height', 'max-height', 'margin', 'padding'],
            },
            {
              name: 'Typography',
              open: false,
              buildProps: [
                'font-family', 'font-size', 'font-weight', 'letter-spacing',
                'color', 'line-height', 'text-align', 'text-decoration', 'text-shadow', 'text-transform',
              ],
            },
            {
              name: 'Decorations',
              open: false,
              buildProps: ['background', 'background-color', 'background-image', 'background-size', 'background-position', 'border-radius', 'border', 'box-shadow'],
            },
            {
              name: 'Extra',
              open: false,
              buildProps: ['opacity', 'transition', 'transform', 'cursor', 'overflow'],
            },
          ],
        },
        traitManager: {
          appendTo: '#traits-container',
        },
        selectorManager: {
          appendTo: '#selectors-container',
        },
      });

      // ============================================
      // LAYOUT BLOCKS
      // ============================================

      editor.BlockManager.add('section', {
        label: 'Section',
        category: 'Layout',
        attributes: { class: 'fa fa-square-o' },
        content: `<section class="py-16 px-4">
          <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-8">Section Title</h2>
            <p class="text-gray-600 text-center max-w-2xl mx-auto">
              Add your content here. This is a placeholder text.
            </p>
          </div>
        </section>`,
      });

      editor.BlockManager.add('container', {
        label: 'Container',
        category: 'Layout',
        attributes: { class: 'fa fa-arrows-alt' },
        content: `<div class="max-w-6xl mx-auto px-4"></div>`,
      });

      editor.BlockManager.add('two-columns', {
        label: '2 Columns',
        category: 'Layout',
        attributes: { class: 'fa fa-columns' },
        content: `<div class="grid grid-cols-1 md:grid-cols-2 gap-8 py-12 px-4">
          <div class="p-6 bg-gray-50 rounded-lg">
            <h3 class="text-xl font-semibold mb-4">Column 1</h3>
            <p class="text-gray-600">Add your content here.</p>
          </div>
          <div class="p-6 bg-gray-50 rounded-lg">
            <h3 class="text-xl font-semibold mb-4">Column 2</h3>
            <p class="text-gray-600">Add your content here.</p>
          </div>
        </div>`,
      });

      editor.BlockManager.add('three-columns', {
        label: '3 Columns',
        category: 'Layout',
        attributes: { class: 'fa fa-th' },
        content: `<div class="grid grid-cols-1 md:grid-cols-3 gap-6 py-12 px-4">
          <div class="p-6 bg-gray-50 rounded-lg">
            <h3 class="text-xl font-semibold mb-4">Column 1</h3>
            <p class="text-gray-600">Add your content here.</p>
          </div>
          <div class="p-6 bg-gray-50 rounded-lg">
            <h3 class="text-xl font-semibold mb-4">Column 2</h3>
            <p class="text-gray-600">Add your content here.</p>
          </div>
          <div class="p-6 bg-gray-50 rounded-lg">
            <h3 class="text-xl font-semibold mb-4">Column 3</h3>
            <p class="text-gray-600">Add your content here.</p>
          </div>
        </div>`,
      });

      editor.BlockManager.add('four-columns', {
        label: '4 Columns',
        category: 'Layout',
        attributes: { class: 'fa fa-th-large' },
        content: `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 py-12 px-4">
          <div class="p-4 bg-gray-50 rounded-lg text-center">Column 1</div>
          <div class="p-4 bg-gray-50 rounded-lg text-center">Column 2</div>
          <div class="p-4 bg-gray-50 rounded-lg text-center">Column 3</div>
          <div class="p-4 bg-gray-50 rounded-lg text-center">Column 4</div>
        </div>`,
      });

      editor.BlockManager.add('sidebar-layout', {
        label: 'Sidebar Layout',
        category: 'Layout',
        attributes: { class: 'fa fa-window-restore' },
        content: `<div class="flex flex-col md:flex-row gap-8 py-12 px-4 max-w-6xl mx-auto">
          <div class="md:w-2/3 p-6 bg-white rounded-lg shadow">
            <h2 class="text-2xl font-bold mb-4">Main Content</h2>
            <p class="text-gray-600">Your main content goes here.</p>
          </div>
          <aside class="md:w-1/3 p-6 bg-gray-100 rounded-lg">
            <h3 class="text-lg font-semibold mb-4">Sidebar</h3>
            <p class="text-gray-600">Sidebar content here.</p>
          </aside>
        </div>`,
      });

      // ============================================
      // HERO SECTIONS
      // ============================================

      editor.BlockManager.add('hero', {
        label: 'Hero Basic',
        category: 'Heroes',
        attributes: { class: 'fa fa-star' },
        content: `<section class="py-20 px-4 bg-gradient-to-r from-blue-500 to-purple-600">
          <div class="max-w-4xl mx-auto text-center text-white">
            <h1 class="text-5xl font-bold mb-6">Welcome to Our Site</h1>
            <p class="text-xl mb-8 opacity-90">
              Create something amazing with our landing page builder.
            </p>
            <a href="#" class="inline-block bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">
              Get Started
            </a>
          </div>
        </section>`,
      });

      editor.BlockManager.add('hero-with-image', {
        label: 'Hero + Image',
        category: 'Heroes',
        attributes: { class: 'fa fa-image' },
        content: `<section class="py-20 px-4 bg-white">
          <div class="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6">Build Something Amazing Today</h1>
              <p class="text-xl text-gray-600 mb-8">
                The all-in-one platform for modern businesses. Start free and scale as you grow.
              </p>
              <div class="flex flex-wrap gap-4">
                <a href="#" class="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">Start Free Trial</a>
                <a href="#" class="border border-gray-300 text-gray-700 px-8 py-3 rounded-lg font-semibold hover:bg-gray-50 transition">Learn More</a>
              </div>
            </div>
            <div class="relative">
              <img src="https://placehold.co/600x400/e2e8f0/475569?text=Hero+Image" alt="Hero" class="rounded-lg shadow-xl w-full">
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('hero-video-bg', {
        label: 'Hero Video BG',
        category: 'Heroes',
        attributes: { class: 'fa fa-video-camera' },
        content: `<section class="relative py-32 px-4 bg-gray-900 overflow-hidden">
          <div class="absolute inset-0 bg-black/50 z-10"></div>
          <div class="absolute inset-0 flex items-center justify-center">
            <span class="text-gray-500 text-sm">[Video Background Placeholder]</span>
          </div>
          <div class="relative z-20 max-w-4xl mx-auto text-center text-white">
            <h1 class="text-5xl md:text-6xl font-bold mb-6">Cinematic Experience</h1>
            <p class="text-xl mb-8 opacity-90">Engage your visitors with stunning video backgrounds</p>
            <a href="#" class="inline-block bg-white text-gray-900 px-8 py-4 rounded-lg font-semibold hover:bg-gray-100 transition">
              Watch Demo
            </a>
          </div>
        </section>`,
      });

      editor.BlockManager.add('hero-centered', {
        label: 'Hero Centered',
        category: 'Heroes',
        attributes: { class: 'fa fa-align-center' },
        content: `<section class="py-24 px-4 bg-gradient-to-b from-gray-50 to-white">
          <div class="max-w-3xl mx-auto text-center">
            <span class="inline-block px-4 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium mb-6">New Feature</span>
            <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6">The future of productivity is here</h1>
            <p class="text-xl text-gray-600 mb-8">
              Join over 10,000 teams already using our platform to achieve more.
            </p>
            <form class="flex flex-col sm:flex-row gap-4 justify-center max-w-md mx-auto">
              <input type="email" placeholder="Enter your email" class="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <button type="submit" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">Get Started</button>
            </form>
            <p class="text-sm text-gray-500 mt-4">Free 14-day trial. No credit card required.</p>
          </div>
        </section>`,
      });

      // ============================================
      // FEATURES & BENEFITS
      // ============================================

      editor.BlockManager.add('features', {
        label: 'Features Grid',
        category: 'Features',
        attributes: { class: 'fa fa-th-large' },
        content: `<section class="py-16 px-4 bg-gray-50">
          <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">Powerful Features</h2>
            <p class="text-gray-600 text-center mb-12 max-w-2xl mx-auto">Everything you need to build amazing products</p>
            <div class="grid md:grid-cols-3 gap-8">
              <div class="text-center p-6 bg-white rounded-xl shadow-sm">
                <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i class="fa fa-bolt text-2xl text-blue-600"></i>
                </div>
                <h3 class="text-xl font-semibold mb-2">Lightning Fast</h3>
                <p class="text-gray-600">Optimized for speed and performance</p>
              </div>
              <div class="text-center p-6 bg-white rounded-xl shadow-sm">
                <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i class="fa fa-shield text-2xl text-green-600"></i>
                </div>
                <h3 class="text-xl font-semibold mb-2">Secure</h3>
                <p class="text-gray-600">Enterprise-grade security built-in</p>
              </div>
              <div class="text-center p-6 bg-white rounded-xl shadow-sm">
                <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i class="fa fa-cogs text-2xl text-purple-600"></i>
                </div>
                <h3 class="text-xl font-semibold mb-2">Customizable</h3>
                <p class="text-gray-600">Flexible settings for every need</p>
              </div>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('features-list', {
        label: 'Features List',
        category: 'Features',
        attributes: { class: 'fa fa-list' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 class="text-3xl font-bold mb-6">Why choose us?</h2>
              <ul class="space-y-4">
                <li class="flex items-start gap-4">
                  <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa fa-check text-green-600"></i>
                  </div>
                  <div>
                    <h4 class="font-semibold text-gray-900">Easy Setup</h4>
                    <p class="text-gray-600">Get started in minutes with our intuitive interface</p>
                  </div>
                </li>
                <li class="flex items-start gap-4">
                  <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa fa-check text-green-600"></i>
                  </div>
                  <div>
                    <h4 class="font-semibold text-gray-900">24/7 Support</h4>
                    <p class="text-gray-600">Our team is always here to help you succeed</p>
                  </div>
                </li>
                <li class="flex items-start gap-4">
                  <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa fa-check text-green-600"></i>
                  </div>
                  <div>
                    <h4 class="font-semibold text-gray-900">Regular Updates</h4>
                    <p class="text-gray-600">New features and improvements every month</p>
                  </div>
                </li>
              </ul>
            </div>
            <div>
              <img src="https://placehold.co/500x400/e2e8f0/475569?text=Feature+Image" alt="Features" class="rounded-lg shadow-lg w-full">
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('features-icons', {
        label: 'Features Icons',
        category: 'Features',
        attributes: { class: 'fa fa-star-o' },
        content: `<section class="py-16 px-4 bg-gray-900 text-white">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Everything You Need</h2>
              <p class="text-gray-400 max-w-2xl mx-auto">A complete toolkit for your business</p>
            </div>
            <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
              <div class="text-center">
                <i class="fa fa-line-chart text-4xl text-blue-400 mb-4"></i>
                <h3 class="font-semibold mb-2">Analytics</h3>
                <p class="text-gray-400 text-sm">Deep insights into your data</p>
              </div>
              <div class="text-center">
                <i class="fa fa-users text-4xl text-green-400 mb-4"></i>
                <h3 class="font-semibold mb-2">Team Collaboration</h3>
                <p class="text-gray-400 text-sm">Work together seamlessly</p>
              </div>
              <div class="text-center">
                <i class="fa fa-cloud text-4xl text-purple-400 mb-4"></i>
                <h3 class="font-semibold mb-2">Cloud Storage</h3>
                <p class="text-gray-400 text-sm">Secure cloud infrastructure</p>
              </div>
              <div class="text-center">
                <i class="fa fa-mobile text-4xl text-pink-400 mb-4"></i>
                <h3 class="font-semibold mb-2">Mobile Ready</h3>
                <p class="text-gray-400 text-sm">Access from any device</p>
              </div>
            </div>
          </div>
        </section>`,
      });

      // ============================================
      // PRICING
      // ============================================

      editor.BlockManager.add('pricing', {
        label: 'Pricing Table',
        category: 'Pricing',
        attributes: { class: 'fa fa-dollar' },
        content: `<section class="py-16 px-4 bg-gray-50">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Simple, Transparent Pricing</h2>
              <p class="text-gray-600">Choose the plan that's right for you</p>
            </div>
            <div class="grid md:grid-cols-3 gap-8">
              <div class="bg-white rounded-2xl shadow-sm p-8 border border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Starter</h3>
                <p class="text-gray-500 text-sm mb-4">For individuals</p>
                <div class="mb-6">
                  <span class="text-4xl font-bold">$9</span>
                  <span class="text-gray-500">/month</span>
                </div>
                <ul class="space-y-3 mb-8">
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> 5 Projects</li>
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> 10GB Storage</li>
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> Email Support</li>
                </ul>
                <a href="#" class="block text-center py-3 px-6 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition">Get Started</a>
              </div>
              <div class="bg-blue-600 rounded-2xl shadow-lg p-8 text-white transform scale-105">
                <div class="flex justify-between items-center mb-2">
                  <h3 class="text-lg font-semibold">Professional</h3>
                  <span class="text-xs bg-yellow-400 text-gray-900 px-2 py-1 rounded-full font-medium">Popular</span>
                </div>
                <p class="text-blue-200 text-sm mb-4">For growing teams</p>
                <div class="mb-6">
                  <span class="text-4xl font-bold">$29</span>
                  <span class="text-blue-200">/month</span>
                </div>
                <ul class="space-y-3 mb-8">
                  <li class="flex items-center gap-2 text-sm"><i class="fa fa-check text-yellow-400"></i> Unlimited Projects</li>
                  <li class="flex items-center gap-2 text-sm"><i class="fa fa-check text-yellow-400"></i> 100GB Storage</li>
                  <li class="flex items-center gap-2 text-sm"><i class="fa fa-check text-yellow-400"></i> Priority Support</li>
                  <li class="flex items-center gap-2 text-sm"><i class="fa fa-check text-yellow-400"></i> Advanced Analytics</li>
                </ul>
                <a href="#" class="block text-center py-3 px-6 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition">Get Started</a>
              </div>
              <div class="bg-white rounded-2xl shadow-sm p-8 border border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Enterprise</h3>
                <p class="text-gray-500 text-sm mb-4">For large organizations</p>
                <div class="mb-6">
                  <span class="text-4xl font-bold">$99</span>
                  <span class="text-gray-500">/month</span>
                </div>
                <ul class="space-y-3 mb-8">
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> Everything in Pro</li>
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> Unlimited Storage</li>
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> Dedicated Support</li>
                  <li class="flex items-center gap-2 text-sm text-gray-600"><i class="fa fa-check text-green-500"></i> Custom Integrations</li>
                </ul>
                <a href="#" class="block text-center py-3 px-6 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition">Contact Sales</a>
              </div>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('pricing-simple', {
        label: 'Pricing Cards',
        category: 'Pricing',
        attributes: { class: 'fa fa-credit-card' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-4xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Choose Your Plan</h2>
            </div>
            <div class="grid md:grid-cols-2 gap-8">
              <div class="border-2 border-gray-200 rounded-xl p-8 hover:border-blue-500 transition cursor-pointer">
                <h3 class="text-xl font-bold mb-2">Monthly</h3>
                <div class="text-3xl font-bold text-blue-600 mb-4">$19<span class="text-base text-gray-500 font-normal">/mo</span></div>
                <p class="text-gray-600 mb-6">Perfect for trying out our service</p>
                <a href="#" class="block text-center py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition">Subscribe</a>
              </div>
              <div class="border-2 border-blue-500 rounded-xl p-8 relative">
                <span class="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white text-xs px-3 py-1 rounded-full">Save 20%</span>
                <h3 class="text-xl font-bold mb-2">Annual</h3>
                <div class="text-3xl font-bold text-blue-600 mb-4">$15<span class="text-base text-gray-500 font-normal">/mo</span></div>
                <p class="text-gray-600 mb-6">Billed annually ($180/year)</p>
                <a href="#" class="block text-center py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition">Subscribe</a>
              </div>
            </div>
          </div>
        </section>`,
      });

      // ============================================
      // TESTIMONIALS & SOCIAL PROOF
      // ============================================

      editor.BlockManager.add('testimonial', {
        label: 'Testimonial Card',
        category: 'Testimonials',
        attributes: { class: 'fa fa-quote-left' },
        content: `<div class="bg-white p-8 rounded-xl shadow-lg max-w-md mx-auto">
          <div class="flex text-yellow-400 mb-4">
            <i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i>
          </div>
          <p class="text-gray-600 italic mb-6">
            "This product has completely transformed how we work. The team is incredibly responsive and the features are exactly what we needed."
          </p>
          <div class="flex items-center">
            <img src="https://placehold.co/48x48/e2e8f0/475569?text=JD" alt="Avatar" class="w-12 h-12 rounded-full mr-4">
            <div>
              <p class="font-semibold text-gray-900">John Doe</p>
              <p class="text-sm text-gray-500">CEO, TechCorp</p>
            </div>
          </div>
        </div>`,
      });

      editor.BlockManager.add('testimonials-grid', {
        label: 'Testimonials Grid',
        category: 'Testimonials',
        attributes: { class: 'fa fa-th' },
        content: `<section class="py-16 px-4 bg-gray-50">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">What Our Customers Say</h2>
              <p class="text-gray-600">Trusted by thousands of businesses worldwide</p>
            </div>
            <div class="grid md:grid-cols-3 gap-8">
              <div class="bg-white p-6 rounded-xl shadow-sm">
                <div class="flex text-yellow-400 text-sm mb-4">
                  <i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i>
                </div>
                <p class="text-gray-600 mb-4">"Absolutely love it! Made our workflow so much easier."</p>
                <div class="flex items-center">
                  <img src="https://placehold.co/40x40/e2e8f0/475569?text=SM" class="w-10 h-10 rounded-full mr-3">
                  <div>
                    <p class="font-medium text-sm">Sarah Miller</p>
                    <p class="text-xs text-gray-500">Marketing Manager</p>
                  </div>
                </div>
              </div>
              <div class="bg-white p-6 rounded-xl shadow-sm">
                <div class="flex text-yellow-400 text-sm mb-4">
                  <i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i>
                </div>
                <p class="text-gray-600 mb-4">"The best investment we've made for our business."</p>
                <div class="flex items-center">
                  <img src="https://placehold.co/40x40/e2e8f0/475569?text=MJ" class="w-10 h-10 rounded-full mr-3">
                  <div>
                    <p class="font-medium text-sm">Mike Johnson</p>
                    <p class="text-xs text-gray-500">Founder, StartupXYZ</p>
                  </div>
                </div>
              </div>
              <div class="bg-white p-6 rounded-xl shadow-sm">
                <div class="flex text-yellow-400 text-sm mb-4">
                  <i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i>
                </div>
                <p class="text-gray-600 mb-4">"Outstanding support team and amazing features."</p>
                <div class="flex items-center">
                  <img src="https://placehold.co/40x40/e2e8f0/475569?text=EW" class="w-10 h-10 rounded-full mr-3">
                  <div>
                    <p class="font-medium text-sm">Emily Wilson</p>
                    <p class="text-xs text-gray-500">Product Designer</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('logo-cloud', {
        label: 'Logo Cloud',
        category: 'Testimonials',
        attributes: { class: 'fa fa-building' },
        content: `<section class="py-12 px-4 bg-white">
          <div class="max-w-6xl mx-auto">
            <p class="text-center text-gray-500 mb-8">Trusted by leading companies</p>
            <div class="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-60">
              <img src="https://placehold.co/120x40/e2e8f0/475569?text=Logo+1" alt="Company 1" class="h-8 md:h-10">
              <img src="https://placehold.co/120x40/e2e8f0/475569?text=Logo+2" alt="Company 2" class="h-8 md:h-10">
              <img src="https://placehold.co/120x40/e2e8f0/475569?text=Logo+3" alt="Company 3" class="h-8 md:h-10">
              <img src="https://placehold.co/120x40/e2e8f0/475569?text=Logo+4" alt="Company 4" class="h-8 md:h-10">
              <img src="https://placehold.co/120x40/e2e8f0/475569?text=Logo+5" alt="Company 5" class="h-8 md:h-10">
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('stats', {
        label: 'Stats Section',
        category: 'Testimonials',
        attributes: { class: 'fa fa-bar-chart' },
        content: `<section class="py-16 px-4 bg-blue-600 text-white">
          <div class="max-w-6xl mx-auto">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                <div class="text-4xl md:text-5xl font-bold mb-2">10K+</div>
                <div class="text-blue-200">Active Users</div>
              </div>
              <div>
                <div class="text-4xl md:text-5xl font-bold mb-2">95%</div>
                <div class="text-blue-200">Satisfaction Rate</div>
              </div>
              <div>
                <div class="text-4xl md:text-5xl font-bold mb-2">50+</div>
                <div class="text-blue-200">Countries</div>
              </div>
              <div>
                <div class="text-4xl md:text-5xl font-bold mb-2">24/7</div>
                <div class="text-blue-200">Support</div>
              </div>
            </div>
          </div>
        </section>`,
      });

      // ============================================
      // CTA SECTIONS
      // ============================================

      editor.BlockManager.add('cta', {
        label: 'CTA Basic',
        category: 'CTA',
        attributes: { class: 'fa fa-bullhorn' },
        content: `<section class="py-16 px-4 bg-blue-600">
          <div class="max-w-4xl mx-auto text-center text-white">
            <h2 class="text-3xl font-bold mb-4">Ready to get started?</h2>
            <p class="text-lg mb-8 opacity-90">
              Join thousands of satisfied customers today.
            </p>
            <a href="#" class="inline-block bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">
              Sign Up Now
            </a>
          </div>
        </section>`,
      });

      editor.BlockManager.add('cta-split', {
        label: 'CTA Split',
        category: 'CTA',
        attributes: { class: 'fa fa-columns' },
        content: `<section class="py-16 px-4 bg-gradient-to-r from-purple-600 to-blue-600">
          <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
            <div class="text-white">
              <h2 class="text-3xl font-bold mb-2">Start your free trial</h2>
              <p class="opacity-90">No credit card required. Cancel anytime.</p>
            </div>
            <div class="flex flex-wrap gap-4">
              <a href="#" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">Get Started</a>
              <a href="#" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white/10 transition">Learn More</a>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('cta-newsletter', {
        label: 'Newsletter CTA',
        category: 'CTA',
        attributes: { class: 'fa fa-envelope' },
        content: `<section class="py-16 px-4 bg-gray-100">
          <div class="max-w-2xl mx-auto text-center">
            <h2 class="text-3xl font-bold mb-4">Subscribe to our newsletter</h2>
            <p class="text-gray-600 mb-8">Get the latest updates and news delivered to your inbox.</p>
            <form class="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
              <input type="email" placeholder="Enter your email" class="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <button type="submit" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition whitespace-nowrap">Subscribe</button>
            </form>
          </div>
        </section>`,
      });

      // ============================================
      // TEAM
      // ============================================

      editor.BlockManager.add('team', {
        label: 'Team Grid',
        category: 'Team',
        attributes: { class: 'fa fa-users' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Meet Our Team</h2>
              <p class="text-gray-600">The talented people behind our success</p>
            </div>
            <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
              <div class="text-center">
                <img src="https://placehold.co/200x200/e2e8f0/475569?text=Team+1" alt="Team member" class="w-32 h-32 rounded-full mx-auto mb-4 object-cover">
                <h3 class="font-semibold text-lg">Sarah Johnson</h3>
                <p class="text-gray-500 mb-3">CEO & Founder</p>
                <div class="flex justify-center gap-3">
                  <a href="#" class="text-gray-400 hover:text-blue-500"><i class="fa fa-twitter"></i></a>
                  <a href="#" class="text-gray-400 hover:text-blue-700"><i class="fa fa-linkedin"></i></a>
                </div>
              </div>
              <div class="text-center">
                <img src="https://placehold.co/200x200/e2e8f0/475569?text=Team+2" alt="Team member" class="w-32 h-32 rounded-full mx-auto mb-4 object-cover">
                <h3 class="font-semibold text-lg">Mike Chen</h3>
                <p class="text-gray-500 mb-3">CTO</p>
                <div class="flex justify-center gap-3">
                  <a href="#" class="text-gray-400 hover:text-blue-500"><i class="fa fa-twitter"></i></a>
                  <a href="#" class="text-gray-400 hover:text-blue-700"><i class="fa fa-linkedin"></i></a>
                </div>
              </div>
              <div class="text-center">
                <img src="https://placehold.co/200x200/e2e8f0/475569?text=Team+3" alt="Team member" class="w-32 h-32 rounded-full mx-auto mb-4 object-cover">
                <h3 class="font-semibold text-lg">Emily Davis</h3>
                <p class="text-gray-500 mb-3">Head of Design</p>
                <div class="flex justify-center gap-3">
                  <a href="#" class="text-gray-400 hover:text-blue-500"><i class="fa fa-twitter"></i></a>
                  <a href="#" class="text-gray-400 hover:text-blue-700"><i class="fa fa-linkedin"></i></a>
                </div>
              </div>
              <div class="text-center">
                <img src="https://placehold.co/200x200/e2e8f0/475569?text=Team+4" alt="Team member" class="w-32 h-32 rounded-full mx-auto mb-4 object-cover">
                <h3 class="font-semibold text-lg">Alex Wilson</h3>
                <p class="text-gray-500 mb-3">Lead Developer</p>
                <div class="flex justify-center gap-3">
                  <a href="#" class="text-gray-400 hover:text-blue-500"><i class="fa fa-twitter"></i></a>
                  <a href="#" class="text-gray-400 hover:text-blue-700"><i class="fa fa-linkedin"></i></a>
                </div>
              </div>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('team-card', {
        label: 'Team Card',
        category: 'Team',
        attributes: { class: 'fa fa-user' },
        content: `<div class="bg-white rounded-xl shadow-lg overflow-hidden max-w-sm mx-auto">
          <img src="https://placehold.co/400x300/e2e8f0/475569?text=Team+Member" alt="Team member" class="w-full h-48 object-cover">
          <div class="p-6">
            <h3 class="font-bold text-xl mb-1">John Smith</h3>
            <p class="text-blue-600 mb-3">Senior Developer</p>
            <p class="text-gray-600 text-sm mb-4">Passionate about creating elegant solutions to complex problems.</p>
            <div class="flex gap-3">
              <a href="#" class="text-gray-400 hover:text-blue-500"><i class="fa fa-twitter"></i></a>
              <a href="#" class="text-gray-400 hover:text-blue-700"><i class="fa fa-linkedin"></i></a>
              <a href="#" class="text-gray-400 hover:text-gray-700"><i class="fa fa-github"></i></a>
            </div>
          </div>
        </div>`,
      });

      // ============================================
      // FAQ
      // ============================================

      editor.BlockManager.add('faq', {
        label: 'FAQ Section',
        category: 'FAQ',
        attributes: { class: 'fa fa-question-circle' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-3xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Frequently Asked Questions</h2>
              <p class="text-gray-600">Find answers to common questions</p>
            </div>
            <div class="space-y-4">
              <div class="border border-gray-200 rounded-lg">
                <button class="w-full px-6 py-4 text-left font-semibold flex justify-between items-center">
                  <span>What is your refund policy?</span>
                  <i class="fa fa-chevron-down text-gray-400"></i>
                </button>
                <div class="px-6 pb-4 text-gray-600">
                  We offer a 30-day money-back guarantee. If you're not satisfied with our service, contact us for a full refund.
                </div>
              </div>
              <div class="border border-gray-200 rounded-lg">
                <button class="w-full px-6 py-4 text-left font-semibold flex justify-between items-center">
                  <span>How do I get started?</span>
                  <i class="fa fa-chevron-down text-gray-400"></i>
                </button>
                <div class="px-6 pb-4 text-gray-600">
                  Simply sign up for a free account and follow our quick setup wizard. You'll be up and running in minutes.
                </div>
              </div>
              <div class="border border-gray-200 rounded-lg">
                <button class="w-full px-6 py-4 text-left font-semibold flex justify-between items-center">
                  <span>Do you offer customer support?</span>
                  <i class="fa fa-chevron-down text-gray-400"></i>
                </button>
                <div class="px-6 pb-4 text-gray-600">
                  Yes! We offer 24/7 customer support via email and live chat. Premium plans also include phone support.
                </div>
              </div>
              <div class="border border-gray-200 rounded-lg">
                <button class="w-full px-6 py-4 text-left font-semibold flex justify-between items-center">
                  <span>Can I cancel my subscription anytime?</span>
                  <i class="fa fa-chevron-down text-gray-400"></i>
                </button>
                <div class="px-6 pb-4 text-gray-600">
                  Absolutely! You can cancel your subscription at any time from your account settings. No questions asked.
                </div>
              </div>
            </div>
          </div>
        </section>`,
      });

      // ============================================
      // FORMS & CONTACT
      // ============================================

      editor.BlockManager.add('contact-form', {
        label: 'Contact Form',
        category: 'Forms',
        attributes: { class: 'fa fa-envelope-o' },
        content: `<section class="py-16 px-4 bg-gray-50">
          <div class="max-w-2xl mx-auto">
            <div class="text-center mb-8">
              <h2 class="text-3xl font-bold mb-4">Get in Touch</h2>
              <p class="text-gray-600">We'd love to hear from you</p>
            </div>
            <form class="bg-white p-8 rounded-xl shadow-sm">
              <div class="grid md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                  <input type="text" class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="John">
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                  <input type="text" class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Doe">
                </div>
              </div>
              <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input type="email" class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="john@example.com">
              </div>
              <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">Message</label>
                <textarea rows="4" class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Your message..."></textarea>
              </div>
              <button type="submit" class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition">Send Message</button>
            </form>
          </div>
        </section>`,
      });

      editor.BlockManager.add('lead-form', {
        label: 'Lead Capture',
        category: 'Forms',
        attributes: { class: 'fa fa-user-plus' },
        content: `<div class="bg-gradient-to-r from-blue-500 to-purple-600 p-8 rounded-xl text-white max-w-md mx-auto">
          <h3 class="text-2xl font-bold mb-2">Get Your Free Guide</h3>
          <p class="opacity-90 mb-6">Enter your details to download our comprehensive guide.</p>
          <form class="space-y-4">
            <input type="text" placeholder="Your Name" class="w-full px-4 py-3 rounded-lg bg-white/20 placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-white/50 text-white">
            <input type="email" placeholder="Your Email" class="w-full px-4 py-3 rounded-lg bg-white/20 placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-white/50 text-white">
            <button type="submit" class="w-full bg-white text-blue-600 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">Download Now</button>
          </form>
          <p class="text-xs opacity-70 mt-4 text-center">We respect your privacy. Unsubscribe anytime.</p>
        </div>`,
      });

      editor.BlockManager.add('input-field', {
        label: 'Input Field',
        category: 'Forms',
        attributes: { class: 'fa fa-pencil-square-o' },
        content: `<div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Label</label>
          <input type="text" class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Enter text...">
        </div>`,
      });

      editor.BlockManager.add('button', {
        label: 'Button',
        category: 'Forms',
        attributes: { class: 'fa fa-hand-pointer-o' },
        content: `<a href="#" class="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">Click Me</a>`,
      });

      // ============================================
      // MEDIA
      // ============================================

      editor.BlockManager.add('image', {
        label: 'Image',
        category: 'Media',
        attributes: { class: 'fa fa-picture-o' },
        content: `<img src="https://placehold.co/800x400/e2e8f0/475569?text=Your+Image+Here" alt="Image" class="w-full rounded-lg">`,
      });

      editor.BlockManager.add('video-embed', {
        label: 'Video Embed',
        category: 'Media',
        attributes: { class: 'fa fa-youtube-play' },
        content: `<div class="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
          <div class="text-center text-white">
            <i class="fa fa-play-circle text-6xl opacity-80 mb-4"></i>
            <p class="text-sm opacity-60">Replace with your video embed code</p>
          </div>
        </div>`,
      });

      editor.BlockManager.add('gallery', {
        label: 'Image Gallery',
        category: 'Media',
        attributes: { class: 'fa fa-th' },
        content: `<section class="py-12 px-4">
          <div class="max-w-6xl mx-auto">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=1" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=2" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=3" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=4" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=5" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=6" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=7" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
              <img src="https://placehold.co/300x300/e2e8f0/475569?text=8" alt="Gallery" class="w-full aspect-square object-cover rounded-lg hover:opacity-90 transition cursor-pointer">
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('map', {
        label: 'Map Placeholder',
        category: 'Media',
        attributes: { class: 'fa fa-map-marker' },
        content: `<div class="bg-gray-200 rounded-lg h-64 flex items-center justify-center">
          <div class="text-center text-gray-500">
            <i class="fa fa-map-marker text-4xl mb-2"></i>
            <p class="text-sm">Replace with Google Maps embed</p>
          </div>
        </div>`,
      });

      // ============================================
      // NAVIGATION & FOOTER
      // ============================================

      editor.BlockManager.add('navbar', {
        label: 'Navigation',
        category: 'Navigation',
        attributes: { class: 'fa fa-bars' },
        content: `<nav class="py-4 px-6 bg-white shadow-sm">
          <div class="max-w-6xl mx-auto flex items-center justify-between">
            <a href="#" class="text-2xl font-bold text-blue-600">Logo</a>
            <div class="hidden md:flex items-center gap-8">
              <a href="#" class="text-gray-600 hover:text-gray-900">Home</a>
              <a href="#" class="text-gray-600 hover:text-gray-900">Features</a>
              <a href="#" class="text-gray-600 hover:text-gray-900">Pricing</a>
              <a href="#" class="text-gray-600 hover:text-gray-900">About</a>
              <a href="#" class="text-gray-600 hover:text-gray-900">Contact</a>
            </div>
            <a href="#" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition">Get Started</a>
          </div>
        </nav>`,
      });

      editor.BlockManager.add('navbar-dark', {
        label: 'Navigation Dark',
        category: 'Navigation',
        attributes: { class: 'fa fa-bars' },
        content: `<nav class="py-4 px-6 bg-gray-900">
          <div class="max-w-6xl mx-auto flex items-center justify-between">
            <a href="#" class="text-2xl font-bold text-white">Logo</a>
            <div class="hidden md:flex items-center gap-8">
              <a href="#" class="text-gray-300 hover:text-white">Home</a>
              <a href="#" class="text-gray-300 hover:text-white">Features</a>
              <a href="#" class="text-gray-300 hover:text-white">Pricing</a>
              <a href="#" class="text-gray-300 hover:text-white">About</a>
              <a href="#" class="text-gray-300 hover:text-white">Contact</a>
            </div>
            <a href="#" class="bg-white text-gray-900 px-6 py-2 rounded-lg font-medium hover:bg-gray-100 transition">Get Started</a>
          </div>
        </nav>`,
      });

      editor.BlockManager.add('footer', {
        label: 'Footer',
        category: 'Navigation',
        attributes: { class: 'fa fa-window-minimize' },
        content: `<footer class="py-12 px-4 bg-gray-900 text-white">
          <div class="max-w-6xl mx-auto">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
              <div>
                <h4 class="font-semibold mb-4">Company</h4>
                <ul class="space-y-2 text-gray-400">
                  <li><a href="#" class="hover:text-white transition">About</a></li>
                  <li><a href="#" class="hover:text-white transition">Careers</a></li>
                  <li><a href="#" class="hover:text-white transition">Press</a></li>
                </ul>
              </div>
              <div>
                <h4 class="font-semibold mb-4">Product</h4>
                <ul class="space-y-2 text-gray-400">
                  <li><a href="#" class="hover:text-white transition">Features</a></li>
                  <li><a href="#" class="hover:text-white transition">Pricing</a></li>
                  <li><a href="#" class="hover:text-white transition">Security</a></li>
                </ul>
              </div>
              <div>
                <h4 class="font-semibold mb-4">Resources</h4>
                <ul class="space-y-2 text-gray-400">
                  <li><a href="#" class="hover:text-white transition">Blog</a></li>
                  <li><a href="#" class="hover:text-white transition">Help Center</a></li>
                  <li><a href="#" class="hover:text-white transition">Contact</a></li>
                </ul>
              </div>
              <div>
                <h4 class="font-semibold mb-4">Legal</h4>
                <ul class="space-y-2 text-gray-400">
                  <li><a href="#" class="hover:text-white transition">Privacy</a></li>
                  <li><a href="#" class="hover:text-white transition">Terms</a></li>
                  <li><a href="#" class="hover:text-white transition">Cookies</a></li>
                </ul>
              </div>
            </div>
            <div class="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
              <p class="text-gray-400">&copy; 2024 Your Company. All rights reserved.</p>
              <div class="flex gap-4">
                <a href="#" class="text-gray-400 hover:text-white transition"><i class="fa fa-facebook"></i></a>
                <a href="#" class="text-gray-400 hover:text-white transition"><i class="fa fa-twitter"></i></a>
                <a href="#" class="text-gray-400 hover:text-white transition"><i class="fa fa-linkedin"></i></a>
                <a href="#" class="text-gray-400 hover:text-white transition"><i class="fa fa-instagram"></i></a>
              </div>
            </div>
          </div>
        </footer>`,
      });

      editor.BlockManager.add('footer-simple', {
        label: 'Footer Simple',
        category: 'Navigation',
        attributes: { class: 'fa fa-minus' },
        content: `<footer class="py-8 px-4 bg-gray-100">
          <div class="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <p class="text-gray-600">&copy; 2024 Your Company. All rights reserved.</p>
            <div class="flex gap-6">
              <a href="#" class="text-gray-600 hover:text-gray-900 transition">Privacy</a>
              <a href="#" class="text-gray-600 hover:text-gray-900 transition">Terms</a>
              <a href="#" class="text-gray-600 hover:text-gray-900 transition">Contact</a>
            </div>
          </div>
        </footer>`,
      });

      // ============================================
      // CONTENT BLOCKS
      // ============================================

      editor.BlockManager.add('blog-posts', {
        label: 'Blog Posts',
        category: 'Content',
        attributes: { class: 'fa fa-newspaper-o' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Latest Articles</h2>
              <p class="text-gray-600">Stay updated with our latest news and insights</p>
            </div>
            <div class="grid md:grid-cols-3 gap-8">
              <article class="bg-white rounded-xl shadow-sm overflow-hidden">
                <img src="https://placehold.co/400x200/e2e8f0/475569?text=Blog+1" alt="Blog" class="w-full h-48 object-cover">
                <div class="p-6">
                  <span class="text-sm text-blue-600 font-medium">Category</span>
                  <h3 class="text-xl font-bold mt-2 mb-3">How to Boost Your Productivity</h3>
                  <p class="text-gray-600 text-sm mb-4">Learn the best strategies to maximize your daily output...</p>
                  <a href="#" class="text-blue-600 font-medium hover:underline">Read More &rarr;</a>
                </div>
              </article>
              <article class="bg-white rounded-xl shadow-sm overflow-hidden">
                <img src="https://placehold.co/400x200/e2e8f0/475569?text=Blog+2" alt="Blog" class="w-full h-48 object-cover">
                <div class="p-6">
                  <span class="text-sm text-blue-600 font-medium">Category</span>
                  <h3 class="text-xl font-bold mt-2 mb-3">The Future of Remote Work</h3>
                  <p class="text-gray-600 text-sm mb-4">Discover trends shaping the future of distributed teams...</p>
                  <a href="#" class="text-blue-600 font-medium hover:underline">Read More &rarr;</a>
                </div>
              </article>
              <article class="bg-white rounded-xl shadow-sm overflow-hidden">
                <img src="https://placehold.co/400x200/e2e8f0/475569?text=Blog+3" alt="Blog" class="w-full h-48 object-cover">
                <div class="p-6">
                  <span class="text-sm text-blue-600 font-medium">Category</span>
                  <h3 class="text-xl font-bold mt-2 mb-3">Building a Strong Brand</h3>
                  <p class="text-gray-600 text-sm mb-4">Essential tips for creating a memorable brand identity...</p>
                  <a href="#" class="text-blue-600 font-medium hover:underline">Read More &rarr;</a>
                </div>
              </article>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('portfolio', {
        label: 'Portfolio Grid',
        category: 'Content',
        attributes: { class: 'fa fa-briefcase' },
        content: `<section class="py-16 px-4 bg-gray-50">
          <div class="max-w-6xl mx-auto">
            <div class="text-center mb-12">
              <h2 class="text-3xl font-bold mb-4">Our Work</h2>
              <p class="text-gray-600">Check out some of our recent projects</p>
            </div>
            <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              <div class="group relative overflow-hidden rounded-xl">
                <img src="https://placehold.co/400x300/e2e8f0/475569?text=Project+1" alt="Project" class="w-full aspect-[4/3] object-cover group-hover:scale-110 transition duration-300">
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition flex items-end p-6">
                  <div class="text-white">
                    <h3 class="font-bold text-lg">Project Title</h3>
                    <p class="text-sm opacity-80">Web Design</p>
                  </div>
                </div>
              </div>
              <div class="group relative overflow-hidden rounded-xl">
                <img src="https://placehold.co/400x300/e2e8f0/475569?text=Project+2" alt="Project" class="w-full aspect-[4/3] object-cover group-hover:scale-110 transition duration-300">
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition flex items-end p-6">
                  <div class="text-white">
                    <h3 class="font-bold text-lg">Project Title</h3>
                    <p class="text-sm opacity-80">Branding</p>
                  </div>
                </div>
              </div>
              <div class="group relative overflow-hidden rounded-xl">
                <img src="https://placehold.co/400x300/e2e8f0/475569?text=Project+3" alt="Project" class="w-full aspect-[4/3] object-cover group-hover:scale-110 transition duration-300">
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition flex items-end p-6">
                  <div class="text-white">
                    <h3 class="font-bold text-lg">Project Title</h3>
                    <p class="text-sm opacity-80">Mobile App</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>`,
      });

      editor.BlockManager.add('countdown', {
        label: 'Countdown',
        category: 'Content',
        attributes: { class: 'fa fa-clock-o' },
        content: `<div class="py-12 text-center bg-gradient-to-r from-purple-600 to-blue-600">
          <p class="text-lg mb-4 text-white/80">Special offer ends in:</p>
          <div class="flex justify-center gap-4">
            <div class="bg-white/20 backdrop-blur text-white p-4 rounded-xl w-20">
              <span class="text-3xl font-bold block">07</span>
              <p class="text-xs uppercase opacity-80">Days</p>
            </div>
            <div class="bg-white/20 backdrop-blur text-white p-4 rounded-xl w-20">
              <span class="text-3xl font-bold block">12</span>
              <p class="text-xs uppercase opacity-80">Hours</p>
            </div>
            <div class="bg-white/20 backdrop-blur text-white p-4 rounded-xl w-20">
              <span class="text-3xl font-bold block">45</span>
              <p class="text-xs uppercase opacity-80">Mins</p>
            </div>
            <div class="bg-white/20 backdrop-blur text-white p-4 rounded-xl w-20">
              <span class="text-3xl font-bold block">30</span>
              <p class="text-xs uppercase opacity-80">Secs</p>
            </div>
          </div>
        </div>`,
      });

      editor.BlockManager.add('timeline', {
        label: 'Timeline',
        category: 'Content',
        attributes: { class: 'fa fa-list-ol' },
        content: `<section class="py-16 px-4 bg-white">
          <div class="max-w-3xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">How It Works</h2>
            <div class="space-y-8">
              <div class="flex gap-6">
                <div class="flex flex-col items-center">
                  <div class="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">1</div>
                  <div class="w-0.5 h-full bg-gray-200 mt-4"></div>
                </div>
                <div class="pb-8">
                  <h3 class="text-xl font-semibold mb-2">Sign Up</h3>
                  <p class="text-gray-600">Create your free account in just 2 minutes. No credit card required.</p>
                </div>
              </div>
              <div class="flex gap-6">
                <div class="flex flex-col items-center">
                  <div class="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">2</div>
                  <div class="w-0.5 h-full bg-gray-200 mt-4"></div>
                </div>
                <div class="pb-8">
                  <h3 class="text-xl font-semibold mb-2">Configure</h3>
                  <p class="text-gray-600">Customize your settings and invite your team members.</p>
                </div>
              </div>
              <div class="flex gap-6">
                <div class="flex flex-col items-center">
                  <div class="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">3</div>
                </div>
                <div>
                  <h3 class="text-xl font-semibold mb-2">Launch</h3>
                  <p class="text-gray-600">Go live and start seeing results immediately.</p>
                </div>
              </div>
            </div>
          </div>
        </section>`,
      });

      // ============================================
      // BASIC ELEMENTS
      // ============================================

      editor.BlockManager.add('heading', {
        label: 'Heading',
        category: 'Basic',
        attributes: { class: 'fa fa-header' },
        content: `<h2 class="text-3xl font-bold text-gray-900">Your Heading Here</h2>`,
      });

      editor.BlockManager.add('paragraph', {
        label: 'Paragraph',
        category: 'Basic',
        attributes: { class: 'fa fa-paragraph' },
        content: `<p class="text-gray-600 leading-relaxed">Your paragraph text goes here. Write something compelling to engage your visitors.</p>`,
      });

      editor.BlockManager.add('link', {
        label: 'Link',
        category: 'Basic',
        attributes: { class: 'fa fa-link' },
        content: `<a href="#" class="text-blue-600 hover:underline">Click here</a>`,
      });

      editor.BlockManager.add('divider', {
        label: 'Divider',
        category: 'Basic',
        attributes: { class: 'fa fa-minus' },
        content: `<hr class="my-8 border-gray-200">`,
      });

      editor.BlockManager.add('spacer', {
        label: 'Spacer',
        category: 'Basic',
        attributes: { class: 'fa fa-arrows-v' },
        content: `<div class="h-16"></div>`,
      });

      editor.BlockManager.add('quote', {
        label: 'Quote',
        category: 'Basic',
        attributes: { class: 'fa fa-quote-right' },
        content: `<blockquote class="border-l-4 border-blue-600 pl-6 py-2 italic text-gray-600 text-lg">
          "The only way to do great work is to love what you do."
          <footer class="text-sm mt-2 text-gray-500 not-italic">— Steve Jobs</footer>
        </blockquote>`,
      });

      editor.BlockManager.add('list', {
        label: 'List',
        category: 'Basic',
        attributes: { class: 'fa fa-list-ul' },
        content: `<ul class="space-y-2 text-gray-600">
          <li class="flex items-start gap-2"><i class="fa fa-check text-green-500 mt-1"></i> List item one</li>
          <li class="flex items-start gap-2"><i class="fa fa-check text-green-500 mt-1"></i> List item two</li>
          <li class="flex items-start gap-2"><i class="fa fa-check text-green-500 mt-1"></i> List item three</li>
        </ul>`,
      });

      // ============================================
      // SOCIAL
      // ============================================

      editor.BlockManager.add('social-icons', {
        label: 'Social Icons',
        category: 'Social',
        attributes: { class: 'fa fa-share-alt' },
        content: `<div class="flex gap-4 justify-center">
          <a href="#" class="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 transition"><i class="fa fa-facebook"></i></a>
          <a href="#" class="w-10 h-10 bg-sky-500 text-white rounded-full flex items-center justify-center hover:bg-sky-600 transition"><i class="fa fa-twitter"></i></a>
          <a href="#" class="w-10 h-10 bg-pink-600 text-white rounded-full flex items-center justify-center hover:bg-pink-700 transition"><i class="fa fa-instagram"></i></a>
          <a href="#" class="w-10 h-10 bg-blue-700 text-white rounded-full flex items-center justify-center hover:bg-blue-800 transition"><i class="fa fa-linkedin"></i></a>
          <a href="#" class="w-10 h-10 bg-red-600 text-white rounded-full flex items-center justify-center hover:bg-red-700 transition"><i class="fa fa-youtube-play"></i></a>
        </div>`,
      });

      editor.BlockManager.add('social-follow', {
        label: 'Follow Us',
        category: 'Social',
        attributes: { class: 'fa fa-users' },
        content: `<div class="text-center py-8">
          <h3 class="text-xl font-semibold mb-4">Follow Us</h3>
          <p class="text-gray-600 mb-6">Stay connected on social media</p>
          <div class="flex gap-4 justify-center">
            <a href="#" class="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              <i class="fa fa-facebook text-blue-600"></i>
              <span class="text-sm">Facebook</span>
            </a>
            <a href="#" class="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              <i class="fa fa-twitter text-sky-500"></i>
              <span class="text-sm">Twitter</span>
            </a>
            <a href="#" class="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              <i class="fa fa-instagram text-pink-600"></i>
              <span class="text-sm">Instagram</span>
            </a>
          </div>
        </div>`,
      });

      editorRef.current = editor;

      // Prevent GrapesJS fullscreen from covering our custom sidebars
      // (the page is already full-window, so this is a no-op fullscreen)
      editor.Commands.add('fullscreen', { run: () => {}, stop: () => {} });

      if (onLoad) {
        onLoad();
      }

      return () => {
        if (editorRef.current) {
          editorRef.current.destroy();
          editorRef.current = null;
        }
      };
    }, []);

    // Load content when data becomes available
    useEffect(() => {
      if (!editorRef.current) return;

      const editor = editorRef.current;

      // Load initial content
      if (initialData && Object.keys(initialData).length > 0) {
        editor.loadProjectData(initialData);
      } else if (initialHtml) {
        editor.setComponents(initialHtml);
        if (initialCss) {
          editor.setStyle(initialCss);
        }
      }
    }, [initialData, initialHtml, initialCss]);

    // Auto-save every 30 seconds
    useEffect(() => {
      const interval = setInterval(() => {
        handleSave();
      }, 30000);

      return () => clearInterval(interval);
    }, [handleSave]);

    return (
      <div className="flex h-full overflow-hidden relative">

        {/* ── Left Sidebar ──────────────────────────────────────────────── */}
        <div
          className={cn(
            'relative flex flex-col bg-white border-r border-gray-200 shrink-0 transition-all duration-200',
            leftCollapsed ? 'w-0 overflow-hidden' : 'w-64'
          )}
        >
          {/* Tab strip — Blocks | Layers | Forms */}
          <div className="flex border-b border-gray-100 bg-gray-50 shrink-0">
            {(
              [
                { tab: 'blocks', icon: LayoutGrid, label: 'Blocks' },
                { tab: 'layers', icon: Layers,     label: 'Layers' },
                { tab: 'forms',  icon: ClipboardList, label: 'Forms' },
              ] as const
            ).map(({ tab, icon: Icon, label }) => (
              <button
                key={tab}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1 py-2.5 text-xs font-medium border-b-2 transition-colors',
                  leftTab === tab
                    ? 'border-blue-500 text-blue-600 bg-white'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                )}
                onClick={() => setLeftTab(tab)}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {label}
              </button>
            ))}
          </div>

          {/* Blocks — always rendered (GrapesJS appends to it), hidden via class */}
          <div
            id="blocks-container"
            className={cn(
              'flex-1 overflow-y-auto gjs-blocks-container',
              leftTab !== 'blocks' && 'hidden'
            )}
          />

          {/* Layers — always rendered, hidden via class */}
          <div
            id="layers-container"
            className={cn(
              'flex-1 overflow-y-auto',
              leftTab !== 'layers' && 'hidden'
            )}
          />

          {/* Forms panel — React-rendered list */}
          <div
            className={cn(
              'flex flex-col flex-1 overflow-hidden',
              leftTab !== 'forms' && 'hidden'
            )}
          >
            {forms.length === 0 ? (
              <div className="flex flex-col items-center justify-center flex-1 p-6 text-center">
                <ClipboardList className="w-10 h-10 text-gray-200 mb-3" />
                <p className="text-sm font-medium text-gray-500">No active forms</p>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Create a form in the Forms section, then come back to embed it here.
                </p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 px-1 pb-1">
                  Your Forms
                </p>
                {forms.map((form) => (
                  <div
                    key={form.id}
                    className="border border-gray-200 rounded-lg p-3 bg-white hover:border-blue-200 hover:bg-blue-50/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-gray-800 truncate leading-tight">
                          {form.name}
                        </p>
                        <span className="inline-block mt-1.5 text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 capitalize">
                          {form.form_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <button
                        onClick={() => handleInsertForm(form)}
                        className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold rounded-md bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 transition-colors mt-0.5"
                        title={`Insert "${form.name}" form into canvas`}
                      >
                        <Plus className="w-3 h-3" />
                        Insert
                      </button>
                    </div>
                    <a
                      href={`/f/${form.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 flex items-center gap-1 text-[10px] text-gray-400 hover:text-blue-500 transition-colors w-fit"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      Preview form
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Collapse toggle button */}
        <button
          onClick={() => setLeftCollapsed(!leftCollapsed)}
          className="absolute z-20 flex items-center justify-center w-5 h-10 bg-white border border-gray-200 rounded-r-md shadow-sm text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors top-1/2 -translate-y-1/2"
          style={{ left: leftCollapsed ? 0 : 256 }}
          title={leftCollapsed ? 'Show panel' : 'Hide panel'}
        >
          {leftCollapsed
            ? <ChevronRight className="w-3 h-3" />
            : <ChevronLeft className="w-3 h-3" />
          }
        </button>

        {/* ── Canvas ────────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div ref={containerRef} className="flex-1 min-h-0" />
        </div>

        {/* ── Right Sidebar ─────────────────────────────────────────────── */}
        <div className="w-72 bg-white border-l border-gray-200 flex flex-col shrink-0">

          {/* Tab strip */}
          <div className="flex border-b border-gray-100 bg-gray-50 shrink-0">
            <button
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors',
                rightTab === 'style'
                  ? 'border-blue-500 text-blue-600 bg-white'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
              onClick={() => setRightTab('style')}
            >
              <Palette className="w-3.5 h-3.5" />
              Style
            </button>
            <button
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors',
                rightTab === 'properties'
                  ? 'border-blue-500 text-blue-600 bg-white'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
              onClick={() => setRightTab('properties')}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Properties
            </button>
          </div>

          {/* Style tab: selectors + style manager */}
          <div
            className={cn(
              'flex flex-col flex-1 overflow-hidden',
              rightTab !== 'style' && 'hidden'
            )}
          >
            <div
              id="selectors-container"
              className="px-3 py-2 border-b border-gray-100 bg-gray-50/50 shrink-0 min-h-[44px]"
            />
            <div id="styles-container" className="flex-1 overflow-y-auto" />
          </div>

          {/* Properties tab: traits */}
          <div
            className={cn(
              'flex-1 overflow-y-auto',
              rightTab !== 'properties' && 'hidden'
            )}
          >
            <div id="traits-container" className="p-3" />
          </div>
        </div>

        {/* ── GrapesJS CSS Overrides ─────────────────────────────────────── */}
        <style>{`
          /* Hide GrapesJS built-in panel buttons — we use our own sidebars */
          .gjs-pn-panels { display: none !important; }

          /* Canvas fills full height now that built-in panels are gone */
          .gjs-cv-canvas { top: 0 !important; width: 100% !important; }

          /* ── Blocks ─────────────────────────────── */
          .gjs-blocks-container .gjs-block-category {
            border-bottom: 1px solid #f0f0f0;
          }
          .gjs-blocks-container .gjs-block-category .gjs-title {
            background: #f8f9fa;
            padding: 8px 12px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #6b7280;
            cursor: pointer;
            user-select: none;
            border-bottom: 1px solid #f0f0f0;
          }
          .gjs-blocks-container .gjs-block-category .gjs-title:hover {
            background: #f3f4f6;
          }
          .gjs-blocks-container .gjs-blocks-c {
            padding: 6px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
          }
          .gjs-blocks-container .gjs-block {
            width: calc(50% - 3px);
            min-height: 64px;
            margin: 0;
            border-radius: 8px;
            border: 1.5px solid #e5e7eb;
            background: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 8px 6px;
            cursor: grab;
            transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
          }
          .gjs-blocks-container .gjs-block:hover {
            border-color: #3b82f6;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
            transform: translateY(-1px);
          }
          .gjs-blocks-container .gjs-block:active {
            transform: translateY(0);
            cursor: grabbing;
          }
          .gjs-blocks-container .gjs-block__media {
            margin-bottom: 5px;
            font-size: 18px;
            opacity: 0.65;
          }
          .gjs-blocks-container .gjs-block-label {
            font-size: 10px;
            font-weight: 500;
            color: #374151;
            text-align: center;
            line-height: 1.3;
          }

          /* ── Layers ─────────────────────────────── */
          .gjs-layer {
            padding: 7px 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.1s;
          }
          .gjs-layer:hover { background: #f8f9fa; }
          .gjs-layer.gjs-selected { background: #eff6ff; color: #2563eb; }
          .gjs-layer-name { font-size: 12px; color: #374151; }

          /* ── Style Manager ──────────────────────── */
          .gjs-sm-sector-title {
            background: #f8f9fa !important;
            border-top: 1px solid #f0f0f0 !important;
            padding: 9px 12px !important;
            font-size: 10px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            color: #6b7280 !important;
            cursor: pointer !important;
          }
          .gjs-sm-property { padding: 6px 12px; }
          .gjs-sm-label { font-size: 11px; color: #6b7280; font-weight: 500; }

          /* ── Form fields ────────────────────────── */
          .gjs-field { border-radius: 6px; }
          .gjs-field input,
          .gjs-field select,
          .gjs-field textarea {
            border-radius: 5px;
            border: 1.5px solid #e5e7eb;
            padding: 5px 8px;
            font-size: 12px;
            color: #1f2937;
            background: #fff;
            transition: border-color 0.15s;
          }
          .gjs-field input:focus,
          .gjs-field select:focus {
            border-color: #3b82f6;
            outline: none;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
          }

          /* ── Selectors (class manager) ──────────── */
          .gjs-clm-tags { padding: 6px 8px; }
          .gjs-clm-tag {
            border-radius: 4px;
            padding: 3px 8px;
            margin: 2px;
            font-size: 11px;
            background: #eff6ff;
            color: #2563eb;
            border: 1px solid #bfdbfe;
          }
          .gjs-clm-new { font-size: 11px; }

          /* ── Traits ─────────────────────────────── */
          .gjs-trt-trait {
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
          }
          .gjs-label {
            font-size: 11px;
            font-weight: 500;
            color: #6b7280;
            margin-bottom: 4px;
          }

          /* ── GrapesJS colour tokens ─────────────── */
          .gjs-one-bg  { background-color: #fff; }
          .gjs-two-color { color: #1f2937; }
          .gjs-three-bg { background-color: #3b82f6; }
          .gjs-four-color,
          .gjs-four-color-h:hover { color: #3b82f6; }

          /* ── Canvas background & frame ──────────── */
          .gjs-cv-canvas { background: #e5e7eb !important; }
          .gjs-frame-wrapper {
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12) !important;
          }

          /* ── Element selection outline ──────────── */
          .gjs-selected { outline: 2px solid #3b82f6 !important; }
          .gjs-hovered  { outline: 1px dashed #93c5fd !important; }

          /* ── Floating element toolbar ───────────── */
          .gjs-toolbar {
            border-radius: 7px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          }
          .gjs-toolbar-item { padding: 5px 8px; }

          /* ── Resize handles ─────────────────────── */
          .gjs-resizer-h { border-color: #3b82f6; }
          .gjs-resizer-h-br,
          .gjs-resizer-h-tl,
          .gjs-resizer-h-tr,
          .gjs-resizer-h-bl {
            background: #3b82f6;
            border-radius: 2px;
          }

          /* ── Buttons ────────────────────────────── */
          .gjs-btn-prim {
            background-color: #3b82f6;
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
            font-weight: 500;
          }
          .gjs-btn-prim:hover { background-color: #2563eb; }
        `}</style>
      </div>
    );
  }
);

GrapesJSEditor.displayName = 'GrapesJSEditor';

export default GrapesJSEditor;
