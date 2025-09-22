'use client'

import { redirect } from 'next/navigation'

export default function RegisterPage() {
  // Redirect to the senior registration page
  redirect('/auth/register/senior')

  return null
}