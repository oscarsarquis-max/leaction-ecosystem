package br.com.actionfinance.application.integration;

import org.springframework.stereotype.Component;

import java.util.UUID;

/**
 * Ganchos sem efeito em produção. O IT de concorrência substitui os runnables.
 */
@Component
public class LookupConcurrencyGate {

    private volatile Runnable afterReadForRecover = LookupConcurrencyGate::noop;
    private volatile Runnable afterRecover = LookupConcurrencyGate::noop;
    private volatile Runnable afterBeginAttempt = LookupConcurrencyGate::noop;
    private volatile Runnable beforeRecover = LookupConcurrencyGate::noop;
    private volatile Runnable beforeComplete = LookupConcurrencyGate::noop;
    private final ThreadLocal<Boolean> suppressRecover = ThreadLocal.withInitial(() -> Boolean.FALSE);

    public void afterReadForRecover(UUID operationId) {
        afterReadForRecover.run();
    }

    public void afterRecover(UUID operationId) {
        afterRecover.run();
    }

    public void afterBeginAttempt(UUID attemptId) {
        afterBeginAttempt.run();
    }

    public void beforeRecover(UUID operationId) {
        beforeRecover.run();
    }

    public void beforeComplete(UUID attemptId) {
        beforeComplete.run();
    }

    public void setAfterReadForRecover(Runnable action) {
        afterReadForRecover = action == null ? LookupConcurrencyGate::noop : action;
    }

    public void setAfterRecover(Runnable action) {
        afterRecover = action == null ? LookupConcurrencyGate::noop : action;
    }

    public void setAfterBeginAttempt(Runnable action) {
        afterBeginAttempt = action == null ? LookupConcurrencyGate::noop : action;
    }

    public void setBeforeRecover(Runnable action) {
        beforeRecover = action == null ? LookupConcurrencyGate::noop : action;
    }

    public void setBeforeComplete(Runnable action) {
        beforeComplete = action == null ? LookupConcurrencyGate::noop : action;
    }

    public void suppressRecoverOnThisThread(boolean suppress) {
        suppressRecover.set(suppress);
    }

    public boolean recoverSuppressed() {
        return Boolean.TRUE.equals(suppressRecover.get());
    }

    public void reset() {
        afterReadForRecover = LookupConcurrencyGate::noop;
        afterRecover = LookupConcurrencyGate::noop;
        afterBeginAttempt = LookupConcurrencyGate::noop;
        beforeRecover = LookupConcurrencyGate::noop;
        beforeComplete = LookupConcurrencyGate::noop;
        suppressRecover.remove();
    }

    private static void noop() {}
}
