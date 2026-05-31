import React from 'react';
import styles from "./loadingSpinner.module.css";

const LoadingSpinner: React.FC = () => {
  return (
    <div className={styles.loadingSpinnerContainer}>
      <div className={styles.loadingSpinner}></div>
    </div>
  );
};

export default LoadingSpinner;