import { useTour } from '../../../store/TourContext';
import { ChatIcon } from '../../../components/ChatIcon/ChatIcon';
import './ActionPromptChips.css';

export function ActionPromptChips({ disabled = false }) {
  const { isWalking, isChatPending, isDemoReady, askHistoricalRag, askGastroRag, t } = useTour();
  const unavailable = disabled || isWalking || isChatPending || !isDemoReady;

  return (
    <div className="action-chips">
      <span className="action-chips__label">{t('suggestedQuestions')}</span>
      <div className="action-chips__grid">
        <button
          type="button"
          className="action-chips__btn action-chips__btn--gastro"
          disabled={unavailable}
          onClick={() => askGastroRag(t('foodQuery'))}
        >
          <span className="action-chips__icon"><ChatIcon name="food" /></span>
          <span>{t('findFood')}</span>
        </button>
        <button
          type="button"
          className="action-chips__btn action-chips__btn--gastro"
          disabled={unavailable}
          onClick={() => askGastroRag(t('coffeeQuery'))}
        >
          <span className="action-chips__icon"><ChatIcon name="coffee" /></span>
          <span>{t('findCoffee')}</span>
        </button>
        <button
          type="button"
          className="action-chips__btn action-chips__btn--rag"
          disabled={unavailable}
          onClick={askHistoricalRag}
        >
          <span className="action-chips__icon"><ChatIcon name="history" /></span>
          <span>{t('exploreHistory')}</span>
        </button>
      </div>
    </div>
  );
}
