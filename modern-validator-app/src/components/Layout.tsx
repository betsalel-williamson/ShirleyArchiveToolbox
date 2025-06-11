import React from 'react'
import '../index.css'

export const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="app-container">
      {children}
    </div>
  )
}
