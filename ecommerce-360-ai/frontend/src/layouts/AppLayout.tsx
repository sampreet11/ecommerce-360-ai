import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, Bot, FileText, Gauge, Home, Menu, Package, ShoppingCart, Truck, Users, X } from "lucide-react";

const NAV = [
  { to: "/", label: "Overview", icon: Home, end: true },
  { to: "/dashboard", label: "Executive Dashboard", icon: Gauge },
  { to: "/chat", label: "AI Analyst", icon: Bot },
  { to: "/sales", label: "Sales", icon: ShoppingCart },
  { to: "/customers", label: "Customers", icon: Users },
  { to: "/products", label: "Products", icon: Package },
  { to: "/operations", label: "Operations", icon: Truck },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const links = (
    <nav className="mt-6 space-y-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
          className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800"}`}>
          <Icon size={17} />{label}
        </NavLink>
      ))}
    </nav>
  );
  const brand = <div className="flex items-center gap-2 text-white"><BarChart3 className="text-brand-500" /><div><div className="text-sm font-semibold leading-tight">E-Commerce 360°</div><div className="text-[11px] text-slate-400">AI Intelligence Platform</div></div></div>;
  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 bg-slate-900 p-5 lg:block">{brand}{links}
        <p className="mt-8 text-[11px] leading-relaxed text-slate-500">Historical Olist data (2016-2018). Revenue = item price, not profit.</p></aside>
      <header className="flex items-center justify-between bg-slate-900 p-4 lg:hidden">{brand}<button aria-label="Menu" className="text-white" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button></header>
      {open && <div className="bg-slate-900 px-4 pb-4 lg:hidden">{links}</div>}
      <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8"><Outlet /></main>
    </div>
  );
}
