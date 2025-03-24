import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import OnboardingTooltip from '@/components/ui/OnboardingTooltip';

export interface OnboardingStep {
  targetId: string;
  title: string;
  content: string;
  position?: 'top' | 'right' | 'bottom' | 'left';
}

interface OnboardingContextType {
  isOnboardingActive: boolean;
  startOnboarding: () => void;
  skipOnboarding: () => void;
  currentStep: number;
  hasCompletedOnboarding: boolean;
  resetOnboarding: () => void;
}

const OnboardingContext = createContext<OnboardingContextType>({
  isOnboardingActive: false,
  startOnboarding: () => {},
  skipOnboarding: () => {},
  currentStep: 0,
  hasCompletedOnboarding: false,
  resetOnboarding: () => {},
});

export const useOnboarding = () => useContext(OnboardingContext);

export const ONBOARDING_STORAGE_KEY = 'doogie-chat-onboarding-completed';

export const OnboardingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isOnboardingActive, setIsOnboardingActive] = useState(false);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);
  
  // Check if user has already completed onboarding
  useEffect(() => {
    const hasCompleted = localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true';
    setHasCompletedOnboarding(hasCompleted);
  }, []);
  
  // Define the onboarding steps
  // These IDs must match the actual DOM element IDs in the application
  const onboardingSteps: OnboardingStep[] = [
    {
      targetId: 'new-chat-button',
      title: 'Start a New Chat',
      content: 'Click here to start a new conversation with Doogie. You can ask questions, get information from your documents, and more.',
      position: 'bottom'
    },
    {
      targetId: 'chat-sidebar',
      title: 'Chat History',
      content: 'All your conversations are saved here. Click on any chat to continue the conversation.',
      position: 'right'
    },
    {
      targetId: 'search-chats',
      title: 'Search Your Chats',
      content: 'Quickly find past conversations by searching for keywords or phrases.',
      position: 'bottom'
    },
    {
      targetId: 'chat-input',
      title: 'Send Messages',
      content: 'Type your message here and press Enter to send. Doogie will respond based on your documents and general knowledge.',
      position: 'top'
    },
    {
      targetId: 'user-menu',
      title: 'User Settings',
      content: 'Access your profile, change theme settings, or log out from here.',
      position: 'left'
    }
  ];
  
  // Start the onboarding tour
  const startOnboarding = useCallback(() => {
    setCurrentStep(1);
    setIsOnboardingActive(true);
  }, []);
  
  // Skip the entire onboarding tour
  const skipOnboarding = useCallback(() => {
    setIsOnboardingActive(false);
    setCurrentStep(0);
    setHasCompletedOnboarding(true);
    localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
  }, []);
  
  // Reset onboarding for testing or if the user wants to see it again
  const resetOnboarding = useCallback(() => {
    localStorage.removeItem(ONBOARDING_STORAGE_KEY);
    setHasCompletedOnboarding(false);
  }, []);
  
  // Move to the next step
  const handleNext = useCallback(() => {
    if (currentStep < onboardingSteps.length) {
      setCurrentStep(current => current + 1);
    } else {
      // Completed all steps
      setIsOnboardingActive(false);
      setCurrentStep(0);
      setHasCompletedOnboarding(true);
      localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
    }
  }, [currentStep, onboardingSteps.length]);
  
  // Move to the previous step
  const handlePrevious = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep(current => current - 1);
    }
  }, [currentStep]);
  
  return (
    <OnboardingContext.Provider
      value={{
        isOnboardingActive,
        startOnboarding,
        skipOnboarding,
        currentStep,
        hasCompletedOnboarding,
        resetOnboarding,
      }}
    >
      {children}
      
      {isOnboardingActive && currentStep > 0 && currentStep <= onboardingSteps.length && (
        <OnboardingTooltip
          targetId={onboardingSteps[currentStep - 1].targetId}
          title={onboardingSteps[currentStep - 1].title}
          content={onboardingSteps[currentStep - 1].content}
          position={onboardingSteps[currentStep - 1].position}
          step={currentStep}
          totalSteps={onboardingSteps.length}
          isOpen={true}
          onClose={skipOnboarding}
          onNext={handleNext}
          onPrevious={handlePrevious}
          onSkip={skipOnboarding}
        />
      )}
    </OnboardingContext.Provider>
  );
};

export default OnboardingContext;
