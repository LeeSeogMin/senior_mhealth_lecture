'use client'

import { redirect } from 'next/navigation'

export default function SeniorRegisterPage() {
  // Redirect to the main register page
  redirect('/register')

  return null
}