import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx';
import './index.css';
import "./styles/tailwind.css";
import "./styles/index.css";
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import PdfViewer from './components/reactPDF/ReactPDF.tsx';



const router =  createBrowserRouter([
  {path:'/', element: <App/>},
  {path:'/file', element: <PdfViewer/>},
])

ReactDOM.createRoot(document.getElementById('root')!).render(
    <RouterProvider router={router}></RouterProvider>
)
