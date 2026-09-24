"use client";

import { ReactNode, useEffect, useRef } from "react";

type ModalProps = {
  children: ReactNode;
  className: string;
  labelledBy: string;
  describedBy?: string;
  onClose: () => void;
  role?: "dialog" | "alertdialog";
};

export function Modal({ children, className, labelledBy, describedBy, onClose, role = "dialog" }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return <dialog
    ref={dialogRef}
    className={`modal-dialog ${className}`}
    role={role}
    aria-modal="true"
    aria-labelledby={labelledBy}
    aria-describedby={describedBy}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onPointerDown={(event) => {
      if (event.target !== event.currentTarget) return;
      const { left, right, top, bottom } = event.currentTarget.getBoundingClientRect();
      if (event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom) onClose();
    }}
  >{children}</dialog>;
}
