import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import './index.css'
import { DigestProvider } from './DigestContext'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import SectorPage from './pages/SectorPage'
import ItemPage from './pages/ItemPage'
import Archive from './pages/Archive'

const router = createBrowserRouter(
  [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'archive', element: <Archive /> },
      { path: 'items/:id', element: <ItemPage /> },
      { path: ':sector', element: <SectorPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') || '/' },
)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DigestProvider>
      <RouterProvider router={router} />
    </DigestProvider>
  </StrictMode>,
)
