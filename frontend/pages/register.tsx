import { useState } from 'react';
import { useRouter } from 'next/router';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import Layout from '@/components/layout/Layout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';

// Define form schema
const registerSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(8, 'Password must be at least 8 characters'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function Register() {
  const { register: registerUser } = useAuth();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const onSubmit = async (data: RegisterFormValues) => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await registerUser(data.email, data.password);
      if (result.success) {
        setSuccess('Registration successful! Your account is pending approval by an administrator. You will be redirected to the login page in 5 seconds.');
        // Add a delay before redirecting to login page so user can see the success message
        setTimeout(() => {
          router.push('/login');
        }, 5000); // 5 second delay
      } else {
        setError(result.error || 'Registration failed. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout title="Register - Doogie Chat Bot">
      <div className="max-w-md mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Register</CardTitle>
            <CardDescription>Create a new account</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              {error && (
                <div className="p-3 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-800 text-red-700 dark:text-red-400 rounded-md">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-800 text-green-700 dark:text-green-400 rounded-md space-y-2">
                  <p>{success}</p>
                  <Button
                    type="button"
                    className="w-full mt-2"
                    onClick={() => router.push('/login')}
                  >
                    Go to Login
                  </Button>
                </div>
              )}
              <Input
                label="Email"
                type="email"
                placeholder="your.email@example.com"
                error={errors.email?.message}
                {...register('email')}
              />
              <Input
                label="Password"
                type="password"
                placeholder="********"
                error={errors.password?.message}
                {...register('password')}
              />
              <Input
                label="Confirm Password"
                type="password"
                placeholder="********"
                error={errors.confirmPassword?.message}
                {...register('confirmPassword')}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Note: New accounts require admin approval before they can be used.
              </p>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button type="submit" className="w-full" isLoading={isLoading}>
                Register
              </Button>
              <p className="text-sm text-center text-gray-600 dark:text-gray-400">
                Already have an account?{' '}
                <Link href="/login" className="text-primary-600 dark:text-primary-400 hover:underline">
                  Login
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </Layout>
  );
}