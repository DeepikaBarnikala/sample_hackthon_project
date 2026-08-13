import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { api, money, percent } from './api'
import './styles.css'

const demo = {
  admin: ['admin@codecommanders.local', 'Admin@123'],
  vendor: ['vendor@codecommanders.local', 'Vendor@123'],
  vendor2: ['vendor2@codecommanders.local', 'Vendor2@123'],
  customer: ['customer@codecommanders.local', 'Customer@123'],
}

function useAuth() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'))
  const login = (data) => { localStorage.setItem('token', data.access_token); localStorage.setItem('user', JSON.stringify(data.user)); setUser(data.user) }
  const logout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); setUser(null) }
  return { user, login, logout }
}

function App() {
  const { user, login, logout } = useAuth()
  const [view, setView] = useState('shop')
  const [cart, setCart] = useState([])
  const [notice, setNotice] = useState('')
  const go = (next) => { setNotice(''); setView(next) }
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0)
  return <>
    <header className="topbar">
      <button className="brand" onClick={() => go('shop')}>Code Commanders <span>Marketplace</span></button>
      <nav>
        <button onClick={() => go('shop')}>Shop</button>
        {user?.role === 'customer' && <button onClick={() => go('orders')}>My Orders</button>}
        {user?.role === 'vendor' && <button onClick={() => go('vendor')}>Vendor Dashboard</button>}
        {user?.role === 'admin' && <button onClick={() => go('admin')}>Admin Dashboard</button>}
        {user ? <button className="outline" onClick={logout}>Logout</button> : <button className="primary" onClick={() => go('auth')}>Login / Register</button>}
        <span className="cartBadge">🛒 {cartCount}</span>
      </nav>
    </header>
    <main>
      {notice && <div className="notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
      {view === 'shop' && <Shop cart={cart} setCart={setCart} setNotice={setNotice} user={user} go={go} />}
      {view === 'auth' && <Auth onLogin={(data) => { login(data); go(data.user.role === 'admin' ? 'admin' : data.user.role === 'vendor' ? 'vendor' : 'shop') }} />}
      {view === 'orders' && user?.role === 'customer' && <Orders setNotice={setNotice} />}
      {view === 'vendor' && user?.role === 'vendor' && <Vendor setNotice={setNotice} />}
      {view === 'admin' && user?.role === 'admin' && <Admin setNotice={setNotice} />}
    </main>
    <footer>Multi-Vendor Marketplace • React + FastAPI + PostgreSQL/SQLite</footer>
  </>
}

function Shop({ cart, setCart, setNotice, user, go }) {
  const [products, setProducts] = useState([]), [categories, setCategories] = useState([])
  const [search, setSearch] = useState(''), [category, setCategory] = useState(''), [vendor, setVendor] = useState('')
  const [vendors, setVendors] = useState([])
  const load = async () => {
    const params = new URLSearchParams(); if (search) params.set('search', search); if (category) params.set('category', category); if (vendor) params.set('vendor_id', vendor)
    const [items, cats, vs] = await Promise.all([api(`/products?${params}`), api('/products/categories'), api('/vendors')]); setProducts(items); setCategories(cats); setVendors(vs.filter(v => v.approved))
  }
  useEffect(() => { load().catch(e => setNotice(e.message)) }, [search, category, vendor])
  const add = (product) => setCart(current => { const existing = current.find(i => i.id === product.id); if (existing) return current.map(i => i.id === product.id ? { ...i, quantity: Math.min(i.quantity + 1, product.stock) } : i); return [...current, { ...product, quantity: 1 }] })
  const changeQty = (id, delta) => setCart(current => current.map(i => i.id === id ? { ...i, quantity: Math.max(1, Math.min(i.quantity + delta, i.stock)) } : i))
  const remove = (id) => setCart(current => current.filter(i => i.id !== id))
  const cartTotal = cart.reduce((sum, i) => sum + i.price * i.quantity, 0)
  const vendorsInCart = new Set(cart.map(i => i.vendor_id)).size
  const checkout = async () => {
    if (!user) return setNotice('Please login as a customer before checkout.')
    if (user.role !== 'customer') return setNotice('Only customers can place orders.')
    if (!cart.length) return
    try { const order = await api('/orders/checkout', { method: 'POST', body: JSON.stringify({ items: cart.map(i => ({ product_id: i.id, quantity: i.quantity })) }) }); setCart([]); setNotice(`Order #${order.id} placed and split into ${order.suborders.length} vendor-wise sub-orders.`); await load() } catch (e) { setNotice(e.message) }
  }
  return <section>
    <div className="hero"><div><p className="eyebrow">UNIFIED STOREFRONT</p><h1>One cart. Multiple vendors. One checkout.</h1><p>Customers shop across approved vendors while each vendor retains independent products, stock and fulfilment.</p></div><div className="heroCard"><b>{products.length}</b><span>visible products</span><b>{money(cartTotal)}</b><span>cart value</span></div></div>
    <div className="filters card"><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search products..."/><select value={category} onChange={e => setCategory(e.target.value)}><option value="">All categories</option>{categories.map(c => <option key={c}>{c}</option>)}</select><select value={vendor} onChange={e => setVendor(e.target.value)}><option value="">All approved vendors</option>{vendors.map(v => <option key={v.id} value={v.id}>{v.business_name}</option>)}</select></div>
    <div className="grid">{products.map(p => <article className="card" key={p.id}><div className="productIcon">{p.category === 'Electronics' ? '🎧' : p.category === 'Fashion' ? '👕' : '📦'}</div><small>{p.category} • Vendor #{p.vendor_id}</small><h3>{p.name}</h3><p>{p.description}</p><div className="row"><strong>{money(p.price)}</strong><span>{p.stock} in stock</span></div><button className="primary full" disabled={!p.stock} onClick={() => add(p)}>Add to cart</button></article>)}</div>
    {cart.length > 0 && <div className="cartPanel card"><div className="sectionTitle"><h2>Your Cart</h2><span>{vendorsInCart} vendor(s)</span></div>{cart.map(i => <div className="cartLine" key={i.id}><div><b>{i.name}</b><small>Vendor #{i.vendor_id} • {money(i.price)} each</small></div><div className="qty"><button onClick={() => changeQty(i.id, -1)}>−</button><b>{i.quantity}</b><button onClick={() => changeQty(i.id, 1)}>+</button></div><strong>{money(i.price * i.quantity)}</strong><button onClick={() => remove(i.id)}>Remove</button></div>)}<div className="cartTotal"><b>Total</b><b>{money(cartTotal)}</b></div><button className="primary full" onClick={checkout}>Checkout</button>{user?.role === 'customer' && <button className="full" onClick={() => go('orders')}>View My Orders</button>}</div>}
  </section>
}

function Auth({ onLogin }) {
  const [mode, setMode] = useState('login'), [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'customer' }), [error, setError] = useState('')
  const submit = async e => { e.preventDefault(); setError(''); try { if (mode === 'register') await api('/auth/register', { method: 'POST', body: JSON.stringify(form) }); onLogin(await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) })) } catch (e) { setError(e.message) } }
  const fill = role => setForm({ ...form, email: demo[role][0], password: demo[role][1] })
  return <div className="auth card"><h2>{mode === 'login' ? 'Welcome back' : 'Create an account'}</h2>{error && <p className="error">{error}</p>}<form onSubmit={submit}>{mode === 'register' && <><input placeholder="Full name" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} required/><select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}><option value="customer">Customer</option><option value="vendor">Vendor</option></select></>}<input type="email" placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required/><input type="password" minLength="8" placeholder="Password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required/><button className="primary full">{mode === 'login' ? 'Login' : 'Register'}</button></form><button className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Need an account? Register' : 'Already registered? Login'}</button><div className="demo"><b>Demo accounts</b><div className="demoButtons">{Object.keys(demo).map(role => <button key={role} onClick={() => fill(role)}>{role}</button>)}</div><small>Click a role to fill credentials.</small></div></div>
}

function Orders({ setNotice }) {
  const [orders, setOrders] = useState([]), [disputes, setDisputes] = useState([])
  const load = async () => { try { const [o, d] = await Promise.all([api('/orders/my'), api('/disputes/my')]); setOrders(o); setDisputes(d) } catch (e) { setNotice(e.message) } }
  useEffect(() => { load() }, [])
  const dispute = async (order, vendorId) => { const reason = window.prompt('Dispute reason'); if (!reason) return; const description = window.prompt('Describe the issue') || reason; try { await api('/disputes', { method: 'POST', body: JSON.stringify({ order_id: order.id, vendor_id: vendorId, reason, description }) }); setNotice('Dispute submitted to platform admin.'); load() } catch (e) { setNotice(e.message) } }
  return <section><h1>My Orders</h1>{orders.length === 0 ? <div className="empty card">No orders yet. Shop from multiple vendors to create a multi-vendor order.</div> : orders.map(o => <div className="card orderCard" key={o.id}><div className="orderHeader"><div><b>Order #{o.id}</b><small>{new Date(o.created_at).toLocaleString()}</small></div><strong>{money(o.total_amount)}</strong></div><span className="status">Overall: {o.status}</span><div className="items">{o.items.map(i => <span key={i.id}>Product #{i.product_id} × {i.quantity} = {money(i.subtotal)}</span>)}</div><h3>Vendor-wise sub-orders</h3><div className="suborders">{o.suborders.map(s => <div className="suborder" key={s.id}><b>Vendor #{s.vendor_id}</b><span>{money(s.total)}</span><span className="status">{s.status}</span>{!disputes.some(d => d.order_id === o.id && d.vendor_id === s.vendor_id && ['open','investigating'].includes(d.status)) && <button onClick={() => dispute(o, s.vendor_id)}>Raise Dispute</button>}</div>)}</div></div>)}</section>
}

function Vendor({ setNotice }) {
  const [summary, setSummary] = useState({}), [orders, setOrders] = useState([]), [products, setProducts] = useState([]), [profile, setProfile] = useState({ business_name: '', category: '', bank_details: '' })
  const [form, setForm] = useState({ name: '', description: '', price: '', stock: '', category: 'Electronics' }), [editing, setEditing] = useState(null)
  const load = async () => { try { const [s, o, p, profileData] = await Promise.all([api('/vendor/summary'), api('/vendor/orders'), api('/vendor/products'), api('/vendor/profile')]); setSummary(s); setOrders(o); setProducts(p); setProfile({ business_name: profileData.business_name, category: profileData.category, bank_details: profileData.bank_details }) } catch (e) { setNotice(e.message) } }
  useEffect(() => { load() }, [])
  const saveProfile = async e => { e.preventDefault(); try { await api('/vendor/profile', { method: 'POST', body: JSON.stringify({ ...profile, bank_details: profile.bank_details || 'MOCK-ACCOUNT' }) }); setNotice('Vendor profile updated.'); load() } catch (e) { setNotice(e.message) } }
  const saveProduct = async e => { e.preventDefault(); try { const payload = { ...form, price: Number(form.price), stock: Number(form.stock) }; if (editing) await api(`/products/${editing}`, { method: 'PUT', body: JSON.stringify(payload) }); else await api('/products', { method: 'POST', body: JSON.stringify(payload) }); setForm({ name: '', description: '', price: '', stock: '', category: 'Electronics' }); setEditing(null); setNotice(editing ? 'Product updated.' : 'Product listed successfully.'); load() } catch (e) { setNotice(e.message) } }
  const edit = p => { setEditing(p.id); setForm({ name: p.name, description: p.description, price: p.price, stock: p.stock, category: p.category }) }
  const archive = async id => { if (!window.confirm('Archive this product?')) return; try { await api(`/products/${id}`, { method: 'DELETE' }); setNotice('Product archived.'); load() } catch (e) { setNotice(e.message) } }
  const updateStatus = async (id, status) => { try { await api(`/vendor/orders/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); load() } catch (e) { setNotice(e.message) } }
  return <section><h1>Vendor Dashboard</h1><div className="stats"><Stat title="Completed Sales" value={money(summary.completed_sales)} /><Stat title="Commission" value={money(summary.commission)} /><Stat title="Payout" value={money(summary.payout)} /><Stat title="Products" value={summary.products || 0} /></div><div className="two"><div className="card"><h2>Vendor Onboarding Profile</h2><p className="muted">Approved vendors can list products. Bank/payout details are mock data for the hackathon.</p><form onSubmit={saveProfile} className="stack"><input placeholder="Business name" value={profile.business_name} onChange={e => setProfile({ ...profile, business_name: e.target.value })} required/><input placeholder="Business category" value={profile.category} onChange={e => setProfile({ ...profile, category: e.target.value })} required/><input placeholder="Mock bank/payout details" value={profile.bank_details} onChange={e => setProfile({ ...profile, bank_details: e.target.value })}/><button className="primary">Save Profile</button></form><p className={summary.approved ? 'ok' : 'error'}>{summary.approved ? '✓ Approved to list products' : 'Waiting for platform admin approval'}</p></div><div className="card"><h2>{editing ? 'Edit Product' : 'Add Product'}</h2><form onSubmit={saveProduct} className="stack"><input placeholder="Product name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required/><textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}/><input type="number" min="0.01" step="0.01" placeholder="Price" value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} required/><input type="number" min="0" placeholder="Stock" value={form.stock} onChange={e => setForm({ ...form, stock: e.target.value })} required/><input placeholder="Category" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} required/><button className="primary">{editing ? 'Update Product' : 'List Product'}</button>{editing && <button type="button" onClick={() => setEditing(null)}>Cancel Edit</button>}</form></div></div><div className="two"><div className="card"><h2>My Products</h2>{products.map(p => <div className="tableRow" key={p.id}><span><b>{p.name}</b><small>{p.category} • {p.is_active ? 'Active' : 'Archived'}</small></span><span>{money(p.price)}</span><span>Stock: {p.stock}</span><div className="actions">{p.is_active && <button onClick={() => edit(p)}>Edit</button>}{p.is_active && <button onClick={() => archive(p.id)}>Archive</button>}</div></div>)}</div><div className="card"><h2>Vendor Sub-orders</h2>{orders.length === 0 ? <div className="empty">No sub-orders yet.</div> : orders.map(o => <div className="tableRow" key={o.id}><span><b>Sub-order #{o.id}</b><small>Parent order #{o.order_id}</small></span><b>{money(o.total)}</b><select value={o.status} onChange={e => updateStatus(o.id, e.target.value)}><option value="pending">pending</option><option value="processing">processing</option><option value="shipped">shipped</option><option value="delivered">delivered</option><option value="cancelled">cancelled</option></select></div>)}</div></div></section>
}

function Admin({ setNotice }) {
  const [dashboard, setDashboard] = useState({}), [vendors, setVendors] = useState([]), [disputes, setDisputes] = useState([]), [rate, setRate] = useState(.1), [trend, setTrend] = useState([]), [commissions, setCommissions] = useState([]), [payouts, setPayouts] = useState([])
  const load = async () => { try { const [d, v, ds, r, t, c, p] = await Promise.all([api('/admin/dashboard'), api('/admin/vendors'), api('/admin/disputes'), api('/admin/commission-rate'), api('/admin/reports/gmv-trend'), api('/admin/reports/commission'), api('/admin/reports/vendor-payouts')]); setDashboard(d); setVendors(v); setDisputes(ds); setRate(r.rate); setTrend(t); setCommissions(c); setPayouts(p) } catch (e) { setNotice(e.message) } }
  useEffect(() => { load() }, [])
  const approve = async id => { try { await api(`/admin/vendors/${id}/approve`, { method: 'POST' }); setNotice('Vendor approved.'); load() } catch (e) { setNotice(e.message) } }
  const saveRate = async () => { try { await api('/admin/commission-rate', { method: 'PATCH', body: JSON.stringify({ rate: Number(rate) }) }); setNotice('Commission rate updated for future completed sub-orders.'); load() } catch (e) { setNotice(e.message) } }
  const resolve = async (id, status) => { try { await api(`/admin/disputes/${id}`, { method: 'PATCH', body: JSON.stringify({ status, resolution: status === 'resolved' ? 'Resolved by platform admin' : status === 'rejected' ? 'Rejected by platform admin' : 'Case under investigation' }) }); load() } catch (e) { setNotice(e.message) } }
  const maxGMV = Math.max(1, ...trend.map(x => x.gmv))
  return <section><h1>Platform Admin Dashboard</h1><div className="stats"><Stat title="GMV" value={money(dashboard.gmv)} /><Stat title="Completed GMV" value={money(dashboard.completed_gmv)} /><Stat title="Commission Earned" value={money(dashboard.commission)} /><Stat title="Vendor Payout" value={money(dashboard.vendor_payout)} /><Stat title="Orders" value={dashboard.orders || 0} /><Stat title="Open Disputes" value={dashboard.open_disputes || 0} /></div><div className="two"><div className="card"><h2>Vendor Onboarding</h2><p className="muted">Pending vendors: {dashboard.pending_vendors || 0}</p>{vendors.map(v => <div className="tableRow" key={v.id}><span><b>{v.business_name}</b><small>{v.category} • Mock payout: {v.bank_details}</small></span>{v.approved ? <span className="ok">Approved</span> : <button onClick={() => approve(v.id)}>Approve</button>}</div>)}</div><div className="card"><h2>Commission Rate</h2><p className="muted">Applied when a vendor sub-order reaches delivered.</p><div className="rateControl"><input type="number" min="0" max="100" step="0.5" value={(Number(rate) * 100).toFixed(1)} onChange={e => setRate(Number(e.target.value) / 100)} /><span>%</span><button className="primary" onClick={saveRate}>Save</button></div><div className="miniStats"><span>Completed orders <b>{dashboard.completed_orders || 0}</b></span><span>Vendors <b>{dashboard.vendors || 0}</b></span></div></div></div><div className="card"><h2>Platform GMV — 7 Day Trend</h2><div className="trend">{trend.map(x => <div key={x.date}><div className="trendBar" style={{ height: `${Math.max(6, x.gmv / maxGMV * 130)}px` }} title={`${x.date}: ${money(x.gmv)}`}></div><small>{x.date.slice(5)}</small><b>{money(x.gmv)}</b></div>)}</div></div><div className="two"><div className="card"><h2>Vendor Sales & Payouts</h2>{payouts.map(p => <div className="tableRow" key={p.vendor_id}><span><b>{p.vendor}</b><small>Sales {money(p.completed_sales)} • Commission {money(p.commission)}</small></span><strong>{money(p.payout)}</strong></div>)}</div><div className="card"><h2>Commission Earned Report</h2>{commissions.length === 0 ? <div className="empty">No completed sub-orders yet.</div> : commissions.slice(0, 8).map(c => <div className="tableRow" key={c.id}><span><b>{c.vendor}</b><small>Sub-order #{c.suborder_id} • {percent(c.rate)}</small></span><strong>{money(c.amount)}</strong></div>)}</div></div><div className="card"><h2>Dispute Cases</h2>{disputes.length === 0 ? <div className="empty">No disputes.</div> : disputes.map(d => <div className="tableRow" key={d.id}><span><b>#{d.id} • {d.reason}</b><small>Order #{d.order_id} • Vendor #{d.vendor_id}<br/>{d.description}</small></span><span>{d.status}</span>{!['resolved','rejected'].includes(d.status) && <div className="actions"><button onClick={() => resolve(d.id, 'investigating')}>Investigate</button><button onClick={() => resolve(d.id, 'resolved')}>Resolve</button><button onClick={() => resolve(d.id, 'rejected')}>Reject</button></div>}</div>)}</div></section>
}

function Stat({ title, value }) { return <div className="stat"><small>{title}</small><b>{value}</b></div> }
createRoot(document.getElementById('root')).render(<App />)
